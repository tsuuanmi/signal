"""Compare current Signal sample variants with reviewer-derived proxy truth."""

from __future__ import annotations

import csv
import hashlib
import os
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any

from .filesystem import (
    file_sha256,
    sync_directory,
    validate_new_directory,
    write_json,
)
from .model import VARIANT_PROFILE_EVALUATION_SCHEMA_VERSION
from .reviewer_variants import (
    ReviewerVariant,
    json_object,
    load_ground_truth,
    parse_reviewer_variants,
    read_reference,
)

SAMPLE_SCHEMA_VERSION = "signal.sample_evidence/v8"

SAMPLE_COLUMNS = (
    "sample_id",
    "validation_case_id",
    "signal_result_sha256",
    "reviewer_source_events",
    "signal_source_events",
    "canonical_reviewer_groups",
    "canonical_signal_groups",
    "matched_groups",
    "representation_groups",
    "collapsed_reviewer_events",
    "collapsed_signal_events",
    "missing_groups",
    "extra_groups",
    "exact_profile",
)

DIFFERENCE_COLUMNS = (
    "sample_id",
    "validation_case_id",
    "difference",
    "reviewer_tokens",
    "reviewer_positions",
    "reviewer_events",
    "signal_positions",
    "signal_events",
    "reviewer_event_count",
    "signal_event_count",
)


@dataclass(frozen=True)
class SignalVariant:
    """One eligible normalized Signal sample variant."""

    position: int
    reference: str
    alternate: str
    kind: str


@dataclass(frozen=True)
class VariantMatch:
    """One exact or representation-equivalent comparison group."""

    reviewer_indices: tuple[int, ...]
    signal_indices: tuple[int, ...]
    representation_disagreement: bool


@dataclass(frozen=True)
class MutationGroup:
    """One unambiguous contiguous event group and its resulting sequence."""

    indices: tuple[int, ...]
    mutation: str


def sequence_sha256(sequence: str) -> str:
    """Return the normalized reference-sequence identity used by Signal."""
    return hashlib.sha256(sequence.encode()).hexdigest()


def validate_reference_allele(position: int, allele: str, reference: str) -> None:
    """Require a non-wrapping Signal allele to agree with the supplied reference."""
    if not allele:
        raise ValueError("variant reference allele is empty")
    start = position - 1
    if start < 0:
        raise ValueError("variant position must be one-based")
    end = start + len(allele)
    if end > len(reference):
        raise ValueError(
            "variant reference allele crosses the circular origin; "
            "the current evaluator requires a non-seam representation"
        )
    if reference[start:end] != allele:
        raise ValueError(
            "variant reference allele disagrees with the supplied reference"
        )


def load_signal_variants(
    path: Path,
    sample_id: str,
    reference_name: str,
    reference: str,
) -> tuple[list[SignalVariant], str]:
    """Load eligible sample variants plus their configuration identity."""
    value = json_object(path)
    if value.get("schema_version") != SAMPLE_SCHEMA_VERSION:
        raise ValueError(f"{path}: expected {SAMPLE_SCHEMA_VERSION}")
    if value.get("sample_id") != sample_id:
        raise ValueError(f"{path}: sample_id differs from {sample_id!r}")

    provenance = value.get("provenance")
    if not isinstance(provenance, dict):
        raise TypeError(f"{path}: provenance must be an object")
    configuration_sha256 = provenance.get("configuration_sha256")
    if (
        not isinstance(configuration_sha256, str)
        or len(configuration_sha256) != 64
        or any(
            character not in "0123456789abcdef" for character in configuration_sha256
        )
    ):
        raise ValueError(f"{path}: invalid configuration_sha256")

    source_reference = provenance.get("reference")
    if not isinstance(source_reference, dict):
        raise TypeError(f"{path}: reference provenance must be an object")
    if source_reference.get("name") != reference_name:
        raise ValueError(f"{path}: reference name mismatch")
    if source_reference.get("sha256") != sequence_sha256(reference):
        raise ValueError(f"{path}: reference SHA-256 mismatch")

    rows = value.get("variants")
    if not isinstance(rows, list):
        raise TypeError(f"{path}: variants must be an array")

    variants: list[SignalVariant] = []
    seen: set[tuple[int, str, str, str]] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise TypeError(f"{path}: variant {index} must be an object")
        topology = row.get("support_topology")
        if not isinstance(topology, dict):
            raise TypeError(
                f"{path}: variant {index} support_topology must be an object"
            )
        eligible_reads = topology.get("eligible_reads")
        if not isinstance(eligible_reads, int) or eligible_reads < 0:
            raise ValueError(f"{path}: variant {index} has invalid eligible_reads")
        if eligible_reads == 0:
            continue

        position = row.get("position")
        reference_allele = row.get("reference")
        alternate = row.get("alternate")
        kind = row.get("kind")
        if (
            not isinstance(position, int)
            or not isinstance(reference_allele, str)
            or not isinstance(alternate, str)
            or kind not in {"SNV", "INS", "DEL"}
        ):
            raise ValueError(f"{path}: variant {index} has invalid identity")
        validate_reference_allele(position, reference_allele, reference)
        identity = (position, reference_allele, alternate, kind)
        if identity in seen:
            raise ValueError(f"{path}: duplicate eligible variant {identity!r}")
        seen.add(identity)
        variants.append(SignalVariant(*identity))

    return (
        sorted(
            variants,
            key=lambda variant: (
                variant.position,
                variant.reference,
                variant.alternate,
                variant.kind,
            ),
        ),
        configuration_sha256,
    )


def mutated_sequence(
    position: int,
    reference_allele: str,
    alternate: str,
    reference: str,
) -> str:
    """Apply one non-seam variant to the immutable reference."""
    validate_reference_allele(position, reference_allele, reference)
    start = position - 1
    end = start + len(reference_allele)
    return reference[:start] + alternate + reference[end:]


def reviewer_identities(
    variant: ReviewerVariant,
) -> set[tuple[int, str, str, str]]:
    """Expand an IUPAC reviewer SNV into allowed canonical identities."""
    return {
        (variant.position, variant.reference, alternate, variant.kind)
        for alternate in variant.alternates
    }


def signal_identity(variant: SignalVariant) -> tuple[int, str, str, str]:
    """Return the normalized public variant identity."""
    return variant.position, variant.reference, variant.alternate, variant.kind


def reviewer_mutations(variant: ReviewerVariant, reference: str) -> frozenset[str]:
    """Return all full-reference sequences allowed by one reviewer event."""
    return frozenset(
        mutated_sequence(
            variant.position,
            variant.reference,
            alternate,
            reference,
        )
        for alternate in variant.alternates
    )


def signal_mutation(variant: SignalVariant, reference: str) -> str:
    """Return the full-reference sequence produced by one Signal event."""
    return mutated_sequence(
        variant.position,
        variant.reference,
        variant.alternate,
        reference,
    )


def event_span(position: int, reference_allele: str) -> tuple[int, int]:
    """Return the zero-based half-open reference span of one normalized event."""
    start = position - 1
    return start, start + len(reference_allele)


def apply_event_group(
    reference: str,
    events: tuple[tuple[int, str, str], ...],
) -> str | None:
    """Apply non-overlapping reference-coordinate events or return None."""
    normalized: list[tuple[int, int, str]] = []
    for position, reference_allele, alternate in events:
        validate_reference_allele(position, reference_allele, reference)
        start, end = event_span(position, reference_allele)
        normalized.append((start, end, alternate))

    normalized.sort()
    for left, right in pairwise(normalized):
        if right[0] < left[1]:
            return None

    mutated = reference
    for start, end, alternate in reversed(normalized):
        mutated = mutated[:start] + alternate + mutated[end:]
    return mutated


def reviewer_group(
    reviewer: list[ReviewerVariant],
    indices: tuple[int, ...],
    reference: str,
) -> MutationGroup | None:
    """Build one unambiguous reviewer group for exact haplotype comparison."""
    events: list[tuple[int, str, str]] = []
    for index in indices:
        variant = reviewer[index]
        if len(variant.alternates) != 1:
            return None
        alternate = next(iter(variant.alternates))
        events.append((variant.position, variant.reference, alternate))

    mutation = apply_event_group(reference, tuple(events))
    if mutation is None:
        return None
    return MutationGroup(indices, mutation)


def signal_group(
    signal: list[SignalVariant],
    indices: tuple[int, ...],
    reference: str,
) -> MutationGroup | None:
    """Build one Signal group for exact haplotype comparison."""
    events = tuple(
        (signal[index].position, signal[index].reference, signal[index].alternate)
        for index in indices
    )
    mutation = apply_event_group(reference, events)
    if mutation is None:
        return None
    return MutationGroup(indices, mutation)


def contiguous_groups(
    indices: set[int],
    build: Callable[[tuple[int, ...]], MutationGroup | None],
) -> list[MutationGroup]:
    """Enumerate deterministic contiguous groups from one unmatched event ordering."""
    ordered = sorted(indices)
    groups: list[MutationGroup] = []
    for start in range(len(ordered)):
        for stop in range(start + 1, len(ordered) + 1):
            group = build(tuple(ordered[start:stop]))
            if group is not None:
                groups.append(group)
    return groups


def representation_group_matches(
    reviewer: list[ReviewerVariant],
    signal: list[SignalVariant],
    reference: str,
    unmatched_reviewer: set[int],
    unmatched_signal: set[int],
) -> list[VariantMatch]:
    """Match only unambiguous minimal event groups with the same exact haplotype."""
    reviewer_groups = contiguous_groups(
        unmatched_reviewer,
        lambda indices: reviewer_group(reviewer, indices, reference),
    )
    signal_groups = contiguous_groups(
        unmatched_signal,
        lambda indices: signal_group(signal, indices, reference),
    )

    signal_by_mutation: dict[str, list[MutationGroup]] = {}
    for group in signal_groups:
        signal_by_mutation.setdefault(group.mutation, []).append(group)

    candidates: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    for expected in reviewer_groups:
        for observed in signal_by_mutation.get(expected.mutation, ()):
            if len(expected.indices) == 1 and len(observed.indices) == 1:
                continue
            candidates.append((expected.indices, observed.indices))

    minimal: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    for candidate in candidates:
        reviewer_indices, signal_indices = candidate
        reviewer_set = set(reviewer_indices)
        signal_set = set(signal_indices)
        has_proper_equivalent_subgroup = any(
            other != candidate
            and set(other[0]).issubset(reviewer_set)
            and set(other[1]).issubset(signal_set)
            and (
                len(other[0]) < len(reviewer_indices)
                or len(other[1]) < len(signal_indices)
            )
            for other in candidates
        )
        if not has_proper_equivalent_subgroup:
            minimal.append(candidate)

    reviewer_membership: dict[int, int] = {}
    signal_membership: dict[int, int] = {}
    for reviewer_indices, signal_indices in minimal:
        for index in reviewer_indices:
            reviewer_membership[index] = reviewer_membership.get(index, 0) + 1
        for index in signal_indices:
            signal_membership[index] = signal_membership.get(index, 0) + 1

    matches: list[VariantMatch] = []
    for reviewer_indices, signal_indices in sorted(minimal):
        if any(reviewer_membership[index] != 1 for index in reviewer_indices):
            continue
        if any(signal_membership[index] != 1 for index in signal_indices):
            continue
        if not all(index in unmatched_reviewer for index in reviewer_indices):
            continue
        if not all(index in unmatched_signal for index in signal_indices):
            continue
        unmatched_reviewer.difference_update(reviewer_indices)
        unmatched_signal.difference_update(signal_indices)
        matches.append(VariantMatch(reviewer_indices, signal_indices, True))
    return matches


def compare_variants(
    reviewer: list[ReviewerVariant],
    signal: list[SignalVariant],
    reference: str,
) -> tuple[list[VariantMatch], list[int], list[int]]:
    """Match exact events, equivalent events, then equivalent local event groups."""
    unmatched_reviewer = set(range(len(reviewer)))
    unmatched_signal = set(range(len(signal)))
    matches: list[VariantMatch] = []

    for reviewer_index in range(len(reviewer)):
        identities = reviewer_identities(reviewer[reviewer_index])
        exact = next(
            (
                signal_index
                for signal_index in sorted(unmatched_signal)
                if signal_identity(signal[signal_index]) in identities
            ),
            None,
        )
        if exact is None:
            continue
        unmatched_reviewer.remove(reviewer_index)
        unmatched_signal.remove(exact)
        matches.append(VariantMatch((reviewer_index,), (exact,), False))

    for reviewer_index in sorted(unmatched_reviewer.copy()):
        expected = reviewer_mutations(reviewer[reviewer_index], reference)
        equivalent = next(
            (
                signal_index
                for signal_index in sorted(unmatched_signal)
                if signal_mutation(signal[signal_index], reference) in expected
            ),
            None,
        )
        if equivalent is None:
            continue
        unmatched_reviewer.remove(reviewer_index)
        unmatched_signal.remove(equivalent)
        matches.append(VariantMatch((reviewer_index,), (equivalent,), True))

    matches.extend(
        representation_group_matches(
            reviewer,
            signal,
            reference,
            unmatched_reviewer,
            unmatched_signal,
        )
    )
    matches.sort(
        key=lambda match: (
            match.reviewer_indices,
            match.signal_indices,
            match.representation_disagreement,
        )
    )
    return matches, sorted(unmatched_reviewer), sorted(unmatched_signal)


def reviewer_tokens_text(
    reviewer: list[ReviewerVariant],
    indices: tuple[int, ...],
) -> str:
    """Serialize source reviewer token groups without changing their notation."""
    return "|".join(";".join(reviewer[index].tokens) for index in indices)


def reviewer_events_text(
    reviewer: list[ReviewerVariant],
    indices: tuple[int, ...],
) -> str:
    """Serialize parsed reviewer events for audit/debugging."""
    events: list[str] = []
    for index in indices:
        variant = reviewer[index]
        alternate = ",".join(sorted(variant.alternates))
        events.append(
            f"{variant.kind}:{variant.position}:{variant.reference}>{alternate}"
        )
    return "|".join(events)


def signal_events_text(
    signal: list[SignalVariant],
    indices: tuple[int, ...],
) -> str:
    """Serialize normalized Signal events for audit/debugging."""
    return "|".join(
        f"{signal[index].kind}:{signal[index].position}:"
        f"{signal[index].reference}>{signal[index].alternate}"
        for index in indices
    )


def positions_text(positions: list[int]) -> str:
    """Serialize deterministic unique one-based positions."""
    return ";".join(str(position) for position in sorted(set(positions)))


def difference_row(
    sample_id: str,
    case_id: str,
    difference: str,
    reviewer: list[ReviewerVariant],
    signal: list[SignalVariant],
    reviewer_indices: tuple[int, ...],
    signal_indices: tuple[int, ...],
) -> dict[str, Any]:
    """Build one structured missing/extra/representation comparison row."""
    return {
        "sample_id": sample_id,
        "validation_case_id": case_id,
        "difference": difference,
        "reviewer_tokens": reviewer_tokens_text(reviewer, reviewer_indices),
        "reviewer_positions": positions_text(
            [reviewer[index].position for index in reviewer_indices]
        ),
        "reviewer_events": reviewer_events_text(reviewer, reviewer_indices),
        "signal_positions": positions_text(
            [signal[index].position for index in signal_indices]
        ),
        "signal_events": signal_events_text(signal, signal_indices),
        "reviewer_event_count": len(reviewer_indices),
        "signal_event_count": len(signal_indices),
    }


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    columns: tuple[str, ...],
) -> None:
    """Write one deterministic CSV with exact columns."""
    expected = set(columns)
    with path.open("x", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(
            target,
            fieldnames=list(columns),
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        for index, row in enumerate(rows):
            if set(row) != expected:
                raise ValueError(f"CSV row {index} does not match output columns")
            writer.writerow(row)
        target.flush()
        os.fsync(target.fileno())


def ratio(numerator: int, denominator: int) -> float | None:
    """Return a descriptive ratio only when its denominator exists."""
    return numerator / denominator if denominator else None


def publish_evaluation(
    ground_truth_path: Path,
    results_dir: Path,
    reference_path: Path,
    output_dir: Path,
) -> None:
    """Publish a deterministic baseline variant-profile comparison."""
    ground_truth_path = ground_truth_path.resolve()
    results_dir = results_dir.resolve()
    reference_path = reference_path.resolve()
    output_dir = output_dir.resolve()

    if not ground_truth_path.is_file():
        raise ValueError(f"ground truth is not a regular file: {ground_truth_path}")
    if not results_dir.is_dir():
        raise ValueError(f"results directory does not exist: {results_dir}")
    if not reference_path.is_file():
        raise ValueError(f"reference is not a regular file: {reference_path}")

    validate_new_directory(
        output_dir,
        (ground_truth_path, results_dir, reference_path),
    )
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if not output_dir.parent.is_dir() or output_dir.parent.is_symlink():
        raise ValueError(
            f"output parent is not a regular directory: {output_dir.parent}"
        )

    truth = load_ground_truth(ground_truth_path)
    reference_name, reference = read_reference(reference_path)
    sample_rows: list[dict[str, Any]] = []
    difference_rows: list[dict[str, Any]] = []

    total_reviewer_source = 0
    total_signal_source = 0
    total_canonical_reviewer = 0
    total_canonical_signal = 0
    total_matched = 0
    total_representation = 0
    total_collapsed_reviewer = 0
    total_collapsed_signal = 0
    total_missing = 0
    total_extra = 0
    exact_profiles = 0
    configurations: set[str] = set()

    for record in truth["records"]:
        sample_id = record["sample_id"]
        case_id = record["validation_case_id"]
        result_path = results_dir / sample_id / f"{sample_id}.json"
        if not result_path.is_file():
            raise ValueError(f"missing sample result: {result_path}")

        reviewer = parse_reviewer_variants(record["variants"], reference)
        signal, configuration_sha256 = load_signal_variants(
            result_path,
            sample_id,
            reference_name,
            reference,
        )
        configurations.add(configuration_sha256)
        matches, missing, extra = compare_variants(reviewer, signal, reference)
        representation_matches = [
            match for match in matches if match.representation_disagreement
        ]
        representation = len(representation_matches)
        collapsed_reviewer = sum(
            len(match.reviewer_indices) - 1 for match in representation_matches
        )
        collapsed_signal = sum(
            len(match.signal_indices) - 1 for match in representation_matches
        )
        canonical_reviewer = len(reviewer) - collapsed_reviewer
        canonical_signal = len(signal) - collapsed_signal
        if canonical_reviewer != len(matches) + len(missing):
            raise AssertionError("reviewer canonical-group accounting is inconsistent")
        if canonical_signal != len(matches) + len(extra):
            raise AssertionError("Signal canonical-group accounting is inconsistent")
        exact_profile = not missing and not extra and representation == 0

        sample_rows.append(
            {
                "sample_id": sample_id,
                "validation_case_id": case_id,
                "signal_result_sha256": file_sha256(result_path),
                "reviewer_source_events": len(reviewer),
                "signal_source_events": len(signal),
                "canonical_reviewer_groups": canonical_reviewer,
                "canonical_signal_groups": canonical_signal,
                "matched_groups": len(matches),
                "representation_groups": representation,
                "collapsed_reviewer_events": collapsed_reviewer,
                "collapsed_signal_events": collapsed_signal,
                "missing_groups": len(missing),
                "extra_groups": len(extra),
                "exact_profile": "true" if exact_profile else "false",
            }
        )

        for reviewer_index in missing:
            difference_rows.append(
                difference_row(
                    sample_id,
                    case_id,
                    "missing",
                    reviewer,
                    signal,
                    (reviewer_index,),
                    (),
                )
            )
        for signal_index in extra:
            difference_rows.append(
                difference_row(
                    sample_id,
                    case_id,
                    "extra",
                    reviewer,
                    signal,
                    (),
                    (signal_index,),
                )
            )
        for match in representation_matches:
            difference_rows.append(
                difference_row(
                    sample_id,
                    case_id,
                    "representation",
                    reviewer,
                    signal,
                    match.reviewer_indices,
                    match.signal_indices,
                )
            )

        total_reviewer_source += len(reviewer)
        total_signal_source += len(signal)
        total_canonical_reviewer += canonical_reviewer
        total_canonical_signal += canonical_signal
        total_matched += len(matches)
        total_representation += representation
        total_collapsed_reviewer += collapsed_reviewer
        total_collapsed_signal += collapsed_signal
        total_missing += len(missing)
        total_extra += len(extra)
        exact_profiles += int(exact_profile)

    if len(configurations) != 1:
        raise ValueError(
            "sample results do not share one configuration_sha256: "
            + ", ".join(sorted(configurations))
        )
    configuration_sha256 = next(iter(configurations))

    sample_rows.sort(
        key=lambda row: (str(row["sample_id"]), str(row["validation_case_id"]))
    )
    difference_rows.sort(
        key=lambda row: (
            str(row["sample_id"]),
            str(row["validation_case_id"]),
            str(row["difference"]),
            str(row["reviewer_positions"]),
            str(row["signal_positions"]),
            str(row["reviewer_events"]),
            str(row["signal_events"]),
        )
    )

    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        samples_path = stage / "samples.csv"
        differences_path = stage / "differences.csv"
        write_csv(samples_path, sample_rows, SAMPLE_COLUMNS)
        write_csv(differences_path, difference_rows, DIFFERENCE_COLUMNS)

        summary = {
            "samples": len(sample_rows),
            "reviewer_source_events": total_reviewer_source,
            "signal_source_events": total_signal_source,
            "canonical_reviewer_groups": total_canonical_reviewer,
            "canonical_signal_groups": total_canonical_signal,
            "matched_groups": total_matched,
            "proxy_false_positive_groups": total_extra,
            "proxy_false_negative_groups": total_missing,
            "representation_groups": total_representation,
            "collapsed_reviewer_events": total_collapsed_reviewer,
            "collapsed_signal_events": total_collapsed_signal,
            "exact_profiles": exact_profiles,
            "proxy_precision": ratio(total_matched, total_matched + total_extra),
            "proxy_recall": ratio(total_matched, total_matched + total_missing),
            "true_negatives": None,
            "specificity": None,
        }
        write_json(
            stage / "index.json",
            {
                "schema_version": VARIANT_PROFILE_EVALUATION_SCHEMA_VERSION,
                "truth_status": "reviewer_derived_proxy",
                "source_ground_truth_sha256": file_sha256(ground_truth_path),
                "configuration_sha256": configuration_sha256,
                "reference": {
                    "name": reference_name,
                    "sha256": sequence_sha256(reference),
                    "length": len(reference),
                },
                "method": {
                    "signal_profile": (
                        "sample variants with support_topology.eligible_reads > 0"
                    ),
                    "reviewer_notation": (
                        "Sequencher SNV/IUPAC, P.iBASE insertion, PDEL deletion"
                    ),
                    "representation_equivalence": (
                        "exact event identity, then single-event sequence equivalence, "
                        "then unambiguous contiguous multi-event full-reference "
                        "haplotype equivalence"
                    ),
                    "true_negative_policy": (
                        "not estimated from a variant-only proxy; requires an explicit "
                        "reviewed callable/reference denominator"
                    ),
                    "phase_local_attribution": (
                        "none; no hard-coded poly-C or recurrent-locus positions"
                    ),
                },
                "summary": summary,
                "samples_file": "samples.csv",
                "samples_sha256": file_sha256(samples_path),
                "samples_rows": len(sample_rows),
                "samples_columns": list(SAMPLE_COLUMNS),
                "differences_file": "differences.csv",
                "differences_sha256": file_sha256(differences_path),
                "differences_rows": len(difference_rows),
                "differences_columns": list(DIFFERENCE_COLUMNS),
            },
        )
        sync_directory(stage)

        try:
            output_dir.mkdir()
        except FileExistsError as error:
            raise FileExistsError(
                f"output directory appeared while evaluation was running: {output_dir}"
            ) from error
        try:
            for name in ("samples.csv", "differences.csv", "index.json"):
                os.rename(stage / name, output_dir / name)
            sync_directory(output_dir)
            sync_directory(output_dir.parent)
        except OSError:
            shutil.rmtree(output_dir, ignore_errors=True)
            sync_directory(output_dir.parent)
            raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
