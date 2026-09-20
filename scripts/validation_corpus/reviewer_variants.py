"""Reviewer-produced Sequencher variant profiles for local validation."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .filesystem import file_sha256, sync_directory, write_json
from .model import REVIEWER_VARIANT_GROUND_TRUTH_SCHEMA_VERSION

SAMPLE_ID_COLUMN = "Sample ID"
BATCH_COLUMN = "Batch"
ANALYZED_RANGE_COLUMN = "Analyzed Range (Sequencher)"
VARIANT_COLUMN = "Variants (Sequencher)"
REQUIRED_COLUMNS = (
    SAMPLE_ID_COLUMN,
    BATCH_COLUMN,
    ANALYZED_RANGE_COLUMN,
    VARIANT_COLUMN,
)

CASE_ID = re.compile(r"(AB\d+)$")
SNV = re.compile(r"(?P<position>[1-9]\d*)(?P<alternate>[ACGTRYSWKMBDHVN])$")
INSERTION = re.compile(r"(?P<position>[1-9]\d*)\.(?P<index>[1-9]\d*)(?P<base>[ACGT])$")
DELETION = re.compile(r"(?P<position>[1-9]\d*)DEL$")

IUPAC = {
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
    """One reviewer event after grouping Sequencher indel tokens."""

    tokens: tuple[str, ...]
    kind: str
    position: int
    reference: str
    alternates: frozenset[str]


def json_object(path: Path) -> dict[str, Any]:
    """Load one JSON object with a useful validation error."""
    import json

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}: invalid JSON: {error.msg}") from error
    if not isinstance(value, dict):
        raise TypeError(f"{path}: expected a JSON object")
    return value


def read_reference(path: Path) -> tuple[str, str]:
    """Read one canonical A/C/G/T FASTA record."""
    lines = path.read_text(encoding="utf-8").splitlines()
    headers = [line for line in lines if line.startswith(">")]
    if len(headers) != 1:
        raise ValueError(f"{path}: expected exactly one FASTA record")
    name = headers[0][1:].strip()
    if not name:
        raise ValueError(f"{path}: reference name is empty")
    sequence = "".join(
        line.strip().upper() for line in lines if line and not line.startswith(">")
    )
    if not sequence or any(base not in "ACGT" for base in sequence):
        raise ValueError(f"{path}: reference must contain only A/C/G/T")
    return name, sequence


def reference_base(reference: str, position: int) -> str:
    """Return one 1-based reference base."""
    if not 1 <= position <= len(reference):
        raise ValueError(f"reference position out of range: {position}")
    return reference[position - 1]


def validate_tokens(tokens: list[str]) -> None:
    """Validate supported Sequencher token grammar without interpreting biology."""
    insertion_indexes: dict[int, set[int]] = {}
    seen_deletions: set[int] = set()
    seen_snvs: set[int] = set()

    for token in tokens:
        if match := INSERTION.fullmatch(token):
            position = int(match.group("position"))
            index = int(match.group("index"))
            indexes = insertion_indexes.setdefault(position, set())
            if index in indexes:
                raise ValueError(f"duplicate reviewer insertion token: {token}")
            indexes.add(index)
            continue
        if match := DELETION.fullmatch(token):
            position = int(match.group("position"))
            if position in seen_deletions:
                raise ValueError(f"duplicate reviewer deletion token: {token}")
            seen_deletions.add(position)
            continue
        if match := SNV.fullmatch(token):
            position = int(match.group("position"))
            if position in seen_snvs:
                raise ValueError(f"duplicate reviewer SNV token: {token}")
            seen_snvs.add(position)
            continue
        raise ValueError(f"unsupported reviewer variant token: {token!r}")

    for position, indexes in insertion_indexes.items():
        ordered = sorted(indexes)
        if ordered != list(range(1, len(ordered) + 1)):
            raise ValueError(
                f"reviewer insertion indexes are not contiguous at position {position}"
            )


def extract_ground_truth(source_tsv: Path, output_path: Path) -> None:
    """Extract immutable reviewer variant strings into one local JSON artifact."""
    source_tsv = source_tsv.resolve()
    output_path = output_path.resolve()
    if not source_tsv.is_file():
        raise ValueError(f"source TSV is not a regular file: {source_tsv}")
    if output_path.exists() or output_path.is_symlink():
        raise ValueError(f"output file already exists: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with source_tsv.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError(f"{source_tsv}: missing TSV header")
        missing = [
            column for column in REQUIRED_COLUMNS if column not in reader.fieldnames
        ]
        if missing:
            raise ValueError(f"{source_tsv}: missing columns: {', '.join(missing)}")
        source_rows = list(reader)

    records: list[dict[str, Any]] = []
    sample_ids: set[str] = set()
    case_ids: set[str] = set()
    batches: set[str] = set()

    for source_row, row in enumerate(source_rows, 2):
        sample_id = row[SAMPLE_ID_COLUMN].strip()
        if not sample_id or sample_id == SAMPLE_ID_COLUMN:
            continue
        if sample_id in sample_ids:
            raise ValueError(
                f"{source_tsv}:{source_row}: duplicate sample ID {sample_id!r}"
            )

        match = CASE_ID.search(sample_id)
        if match is None:
            raise ValueError(
                f"{source_tsv}:{source_row}: sample ID lacks trailing AB case ID: "
                f"{sample_id!r}"
            )
        case_id = match.group(1)
        if case_id in case_ids:
            raise ValueError(
                f"{source_tsv}:{source_row}: duplicate validation case ID {case_id!r}"
            )

        variants_raw = row[VARIANT_COLUMN]
        variants = variants_raw.split()
        validate_tokens(variants)

        batch = row[BATCH_COLUMN].strip()
        sample_ids.add(sample_id)
        case_ids.add(case_id)
        if batch:
            batches.add(batch)
        records.append(
            {
                "source_row": source_row,
                "sample_id": sample_id,
                "validation_case_id": case_id,
                "batch": batch,
                "analyzed_range": row[ANALYZED_RANGE_COLUMN],
                "variants_raw": variants_raw,
                "variants": variants,
            }
        )

    if not records:
        raise ValueError(f"{source_tsv}: no reviewer records")

    artifact = {
        "schema_version": REVIEWER_VARIANT_GROUND_TRUTH_SCHEMA_VERSION,
        "truth_status": "reviewer_derived_proxy",
        "description": (
            "Reviewer-produced Sequencher sample variant profiles retained as local "
            "validation proxy ground truth. variants_raw preserves the TSV field; "
            "variants is whitespace tokenization only."
        ),
        "source": {
            "file_name": source_tsv.name,
            "sha256": file_sha256(source_tsv),
            "sample_id_column": SAMPLE_ID_COLUMN,
            "variant_column": VARIANT_COLUMN,
            "analyzed_range_column": ANALYZED_RANGE_COLUMN,
            "batches": sorted(batches),
        },
        "record_count": len(records),
        "records": records,
    }
    write_json(output_path, artifact)
    sync_directory(output_path.parent)


def load_ground_truth(path: Path) -> dict[str, Any]:
    """Load and validate a reviewer proxy-ground-truth artifact."""
    value = json_object(path)
    if value.get("schema_version") != REVIEWER_VARIANT_GROUND_TRUTH_SCHEMA_VERSION:
        raise ValueError(f"{path}: unsupported schema_version")
    if value.get("truth_status") != "reviewer_derived_proxy":
        raise ValueError(f"{path}: truth_status must be reviewer_derived_proxy")

    records = value.get("records")
    if not isinstance(records, list) or value.get("record_count") != len(records):
        raise ValueError(f"{path}: invalid record_count/records")
    if not records:
        raise ValueError(f"{path}: no reviewer records")

    case_ids: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise TypeError(f"{path}: record {index} must be an object")
        case_id = record.get("validation_case_id")
        raw = record.get("variants_raw")
        variants = record.get("variants")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"{path}: record {index} lacks validation_case_id")
        if case_id in case_ids:
            raise ValueError(f"{path}: duplicate validation_case_id {case_id!r}")
        if not isinstance(raw, str) or not isinstance(variants, list):
            raise ValueError(f"{path}: record {index} has invalid reviewer variants")
        if not all(isinstance(token, str) for token in variants):
            raise ValueError(f"{path}: record {index} has non-string reviewer token")
        if variants != raw.split():
            raise ValueError(
                f"{path}: record {index} tokenization differs from variants_raw"
            )
        validate_tokens(variants)
        case_ids.add(case_id)
    return value


def parse_reviewer_variants(tokens: list[str], reference: str) -> list[ReviewerVariant]:
    """Interpret supported reviewer notation without changing the source artifact."""
    validate_tokens(tokens)
    variants: list[ReviewerVariant] = []
    insertions: dict[int, dict[int, tuple[str, str]]] = {}
    deletions: dict[int, str] = {}

    for token in tokens:
        if match := INSERTION.fullmatch(token):
            position = int(match.group("position"))
            reference_base(reference, position)
            insertions.setdefault(position, {})[int(match.group("index"))] = (
                token,
                match.group("base"),
            )
            continue
        if match := DELETION.fullmatch(token):
            position = int(match.group("position"))
            reference_base(reference, position)
            deletions[position] = token
            continue

        match = SNV.fullmatch(token)
        if match is None:
            raise AssertionError("validated token did not match a supported grammar")
        position = int(match.group("position"))
        ref = reference_base(reference, position)
        alternates = IUPAC[match.group("alternate")] - {ref}
        if not alternates:
            raise ValueError(f"reviewer SNV does not differ from reference: {token}")
        variants.append(
            ReviewerVariant((token,), "SNV", position, ref, frozenset(alternates))
        )

    for position, by_index in insertions.items():
        ordered = [by_index[index] for index in sorted(by_index)]
        inserted = "".join(base for _, base in ordered)
        ref = reference_base(reference, position)
        variants.append(
            ReviewerVariant(
                tuple(token for token, _ in ordered),
                "INS",
                position,
                ref,
                frozenset({ref + inserted}),
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
        anchor = len(reference) if first == 1 else first - 1
        anchor_base = reference_base(reference, anchor)
        deleted = "".join(reference_base(reference, position) for position in group)
        variants.append(
            ReviewerVariant(
                tuple(deletions[position] for position in group),
                "DEL",
                anchor,
                anchor_base + deleted,
                frozenset({anchor_base}),
            )
        )

    return sorted(
        variants,
        key=lambda variant: (variant.position, variant.kind, variant.tokens),
    )
