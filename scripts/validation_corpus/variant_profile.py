"""Compare Signal sample variant profiles with reviewer-derived proxy truth."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GROUND_TRUTH_SCHEMA_VERSION = "signal.reviewer_variant_ground_truth/v1"
SAMPLE_SCHEMA_VERSION = "signal.sample_evidence/v8"

SNV = re.compile(r"(?P<position>[1-9]\\d*)(?P<alternate>[ACGTRYSWKMBDHVN])$")
INSERTION = re.compile(
    r"(?P<position>[1-9]\\d*)\\.(?P<index>[1-9]\\d*)(?P<base>[ACGT])$"
)
DELETION = re.compile(r"(?P<position>[1-9]\\d*)DEL$")

IUPAC: dict[str, frozenset[str]] = {
    "A": frozenset("A"),
    "C": frozenset("C"),
    "G": frozenset("G"),
    "T": frozenset("T"),
    "R": frozenset("AG"),
    "Y": frozenset("CT"),
    "S": frozenset("CG"),
    "W": frozenset("AT"),
    "K": frozenset("GT"),
    "M": frozenset("AC"),
    "B": frozenset("CGT"),
    "D": frozenset("AGT"),
    "H": frozenset("ACT"),
    "V": frozenset("ACG"),
    "N": frozenset("ACGT"),
}


@dataclass(frozen=True)
class ReviewerVariant:
    tokens: tuple[str, ...]
    kind: str
    position: int
    reference: str
    alternates: frozenset[str]


@dataclass(frozen=True)
class SignalVariant:
    kind: str
    position: int
    reference: str
    alternate: str


@dataclass(frozen=True)
class VariantProfileComparison:
    matched: int
    representation_disagreements: tuple[tuple[ReviewerVariant, SignalVariant], ...]
    missing: tuple[ReviewerVariant, ...]
    extra: tuple[SignalVariant, ...]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sequence_sha256(sequence: str) -> str:
    return hashlib.sha256(sequence.encode()).hexdigest()


def load_reference(path: Path) -> tuple[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    headers = [line for line in lines if line.startswith(">")]
    if len(headers) != 1:
        raise ValueError(f"{path}: expected exactly one FASTA record")
    name = headers[0][1:].strip()
    sequence = "".join(
        line.strip().upper()
        for line in lines
        if line.strip() and not line.startswith(">")
    )
    if not name or not sequence or any(base not in "ACGT" for base in sequence):
        raise ValueError(f"{path}: invalid canonical reference")
    return name, sequence


def json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}: invalid JSON: {error.msg}") from error
    if not isinstance(value, dict):
        raise TypeError(f"{path}: expected a JSON object")
    return value


def load_ground_truth(path: Path) -> dict[str, Any]:
    value = json_object(path)
    if value.get("schema_version") != GROUND_TRUTH_SCHEMA_VERSION:
        raise ValueError(f"{path}: unsupported reviewer ground-truth schema")
    if value.get("truth_status") != "reviewer_derived_proxy":
        raise ValueError(f"{path}: truth_status must be reviewer_derived_proxy")
    records = value.get("records")
    if not isinstance(records, list) or value.get("record_count") != len(records):
        raise ValueError(f"{path}: invalid reviewer record_count")
    seen: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise TypeError(f"{path}: record {index} must be an object")
        case_id = record.get("validation_case_id")
        raw = record.get("variants_raw")
        variants = record.get("variants")
        if (
            not isinstance(case_id, str)
            or not case_id
            or not isinstance(raw, str)
            or not isinstance(variants, list)
            or not all(isinstance(token, str) for token in variants)
        ):
            raise ValueError(f"{path}: invalid reviewer record {index}")
        if case_id in seen:
            raise ValueError(f"{path}: duplicate validation_case_id {case_id!r}")
        if variants != (raw.split() if raw else []):
            raise ValueError(f"{path}: variants differ from variants_raw tokenization")
        seen.add(case_id)
    return value


def reference_base(reference: str, position: int) -> str:
    if not 1 <= position <= len(reference):
        raise ValueError(f"reference position out of range: {position}")
    return reference[position - 1]


def parse_reviewer_variants(
    tokens: list[str], reference: str
) -> tuple[ReviewerVariant, ...]:
    substitutions: list[ReviewerVariant] = []
    insertions: dict[int, dict[int, tuple[str, str]]] = {}
    deletions: dict[int, str] = {}

    for token in tokens:
        if match := INSERTION.fullmatch(token):
            position = int(match.group("position"))
            reference_base(reference, position)
            index = int(match.group("index"))
            by_index = insertions.setdefault(position, {})
            if index in by_index:
                raise ValueError(f"duplicate reviewer insertion index: {token}")
            by_index[index] = (token, match.group("base"))
            continue

        if match := DELETION.fullmatch(token):
            position = int(match.group("position"))
            reference_base(reference, position)
            if position in deletions:
                raise ValueError(f"duplicate reviewer deletion: {token}")
            deletions[position] = token
            continue

        if match := SNV.fullmatch(token):
            position = int(match.group("position"))
            ref = reference_base(reference, position)
            alternates = IUPAC[match.group("alternate")] - {ref}
            if not alternates:
                raise ValueError(f"reviewer substitution does not differ from reference: {token}")
            substitutions.append(
                ReviewerVariant((token,), "SNV", position, ref, frozenset(alternates))
            )
            continue

        raise ValueError(f"unsupported reviewer variant token: {token!r}")

    events = substitutions

    for position, indexed in insertions.items():
        indexes = sorted(indexed)
        if indexes != list(range(1, len(indexes) + 1)):
            raise ValueError(f"reviewer insertion indexes are not contiguous at {position}")
        ordered = [indexed[index] for index in indexes]
        anchor = reference_base(reference, position)
        inserted = "".join(base for _, base in ordered)
        events.append(
            ReviewerVariant(
                tuple(token for token, _ in ordered),
                "INS",
                position,
                anchor,
                frozenset({anchor + inserted}),
            )
        )

    deletion_positions = sorted(deletions)
    groups: list[list[int]] = []
    for position in deletion_positions:
        if not groups or position != groups[-1][-1] + 1:
            groups.append([position])
        else:
            groups[-1].append(position)

    for group in groups:
        first = group[0]
        anchor_position = len(reference) if first == 1 else first - 1
        anchor = reference_base(reference, anchor_position)
        deleted = "".join(reference_base(reference, position) for position in group)
        events.append(
            ReviewerVariant(
                tuple(deletions[position] for position in group),
                "DEL",
                anchor_position,
                anchor + deleted,
                frozenset({anchor}),
            )
        )

    return tuple(sorted(events, key=lambda event: (event.position, event.kind, event.tokens)))


def validate_reference_allele(position: int, allele: str, reference: str) -> None:
    start = position - 1
    if start < 0 or not allele:
        raise ValueError("Signal variant has invalid reference allele")
    end = start + len(allele)
    if end > len(reference):
        raise ValueError("origin-spanning Signal variants are not supported by this comparator")
    if reference[start:end] != allele:
        raise ValueError("Signal variant reference allele disagrees with reference")


def load_signal_variants(
    path: Path, reference_name: str, reference: str
) -> tuple[SignalVariant, ...]:
    value = json_object(path)
    if value.get("schema_version") != SAMPLE_SCHEMA_VERSION:
        raise ValueError(f"{path}: expected {SAMPLE_SCHEMA_VERSION}")

    provenance = value.get("provenance")
    reference_provenance = (
        provenance.get("reference") if isinstance(provenance, dict) else None
    )
    if not isinstance(reference_provenance, dict):
        raise ValueError(f"{path}: missing reference provenance")
    if reference_provenance.get("name") != reference_name:
        raise ValueError(f"{path}: reference name mismatch")
    if reference_provenance.get("sha256") != sequence_sha256(reference):
        raise ValueError(f"{path}: reference SHA-256 mismatch")

    rows = value.get("variants")
    if not isinstance(rows, list):
        raise ValueError(f"{path}: variants must be an array")

    variants: list[SignalVariant] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise TypeError(f"{path}: variant {index} must be an object")
        topology = row.get("support_topology")
        eligible_reads = topology.get("eligible_reads") if isinstance(topology, dict) else None
        if not isinstance(eligible_reads, int) or eligible_reads < 0:
            raise ValueError(f"{path}: variant {index} has invalid eligible_reads")
        if eligible_reads == 0:
            continue

        position = row.get("position")
        ref = row.get("reference")
        alternate = row.get("alternate")
        kind = row.get("kind")
        if (
            not isinstance(position, int)
            or not isinstance(ref, str)
            or not isinstance(alternate, str)
            or kind not in {"SNV", "INS", "DEL"}
        ):
            raise ValueError(f"{path}: variant {index} has invalid identity")
        validate_reference_allele(position, ref, reference)
        variants.append(SignalVariant(kind, position, ref, alternate))

    return tuple(sorted(variants, key=lambda row: (row.position, row.reference, row.alternate, row.kind)))


def mutated_sequence(
    position: int, reference_allele: str, alternate: str, reference: str
) -> str:
    validate_reference_allele(position, reference_allele, reference)
    start = position - 1
    return reference[:start] + alternate + reference[start + len(reference_allele) :]


def reviewer_identities(event: ReviewerVariant) -> set[tuple[int, str, str, str]]:
    return {
        (event.position, event.reference, alternate, event.kind)
        for alternate in event.alternates
    }


def signal_identity(event: SignalVariant) -> tuple[int, str, str, str]:
    return event.position, event.reference, event.alternate, event.kind


def reviewer_mutations(event: ReviewerVariant, reference: str) -> frozenset[str]:
    return frozenset(
        mutated_sequence(event.position, event.reference, alternate, reference)
        for alternate in event.alternates
    )


def compare_profiles(
    reviewer: tuple[ReviewerVariant, ...],
    signal: tuple[SignalVariant, ...],
    reference: str,
) -> VariantProfileComparison:
    remaining_reviewer = set(range(len(reviewer)))
    remaining_signal = set(range(len(signal)))
    matched = 0
    representation: list[tuple[ReviewerVariant, SignalVariant]] = []

    for reviewer_index, expected in enumerate(reviewer):
        identities = reviewer_identities(expected)
        signal_index = next(
            (
                index
                for index in sorted(remaining_signal)
                if signal_identity(signal[index]) in identities
            ),
            None,
        )
        if signal_index is None:
            continue
        remaining_reviewer.remove(reviewer_index)
        remaining_signal.remove(signal_index)
        matched += 1

    for reviewer_index in sorted(remaining_reviewer.copy()):
        expected = reviewer[reviewer_index]
        expected_sequences = reviewer_mutations(expected, reference)
        signal_index = next(
            (
                index
                for index in sorted(remaining_signal)
                if mutated_sequence(
                    signal[index].position,
                    signal[index].reference,
                    signal[index].alternate,
                    reference,
                )
                in expected_sequences
            ),
            None,
        )
        if signal_index is None:
            continue
        remaining_reviewer.remove(reviewer_index)
        remaining_signal.remove(signal_index)
        matched += 1
        representation.append((expected, signal[signal_index]))

    return VariantProfileComparison(
        matched=matched,
        representation_disagreements=tuple(representation),
        missing=tuple(reviewer[index] for index in sorted(remaining_reviewer)),
        extra=tuple(signal[index] for index in sorted(remaining_signal)),
    )
