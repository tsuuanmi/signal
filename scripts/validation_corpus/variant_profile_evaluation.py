"""Compare current Signal sample variants with reviewer-derived proxy truth."""

from __future__ import annotations

import csv
import hashlib
import os
import shutil
import tempfile
from dataclasses import dataclass
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
    "reviewer_variants",
    "signal_variants",
    "matched_variants",
    "representation_disagreements",
    "missing_variants",
    "extra_variants",
    "exact_profile",
)

DIFFERENCE_COLUMNS = (
    "sample_id",
    "validation_case_id",
    "difference",
    "reviewer_tokens",
    "signal_position",
    "signal_reference",
    "signal_alternate",
    "signal_kind",
)


@dataclass(frozen=True)
class SignalVariant:
    """One eligible normalized Signal sample variant."""

    position: int
    reference: str
    alternate: str
    kind: str


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


def compare_variants(
    reviewer: list[ReviewerVariant],
    signal: list[SignalVariant],
    reference: str,
) -> tuple[list[tuple[int, int, bool]], list[int], list[int]]:
    """Match exact identities first, then representation-equivalent single events."""
    unmatched_reviewer = set(range(len(reviewer)))
    unmatched_signal = set(range(len(signal)))
    matches: list[tuple[int, int, bool]] = []

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
        matches.append((reviewer_index, exact, False))

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
        matches.append((reviewer_index, equivalent, True))

    return matches, sorted(unmatched_reviewer), sorted(unmatched_signal)


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

    total_reviewer = 0
    total_signal = 0
    total_matched = 0
    total_representation = 0
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
        representation = sum(
            1
            for _, _, is_representation_disagreement in matches
            if is_representation_disagreement
        )
        exact_profile = not missing and not extra and representation == 0

        sample_rows.append(
            {
                "sample_id": sample_id,
                "validation_case_id": case_id,
                "signal_result_sha256": file_sha256(result_path),
                "reviewer_variants": len(reviewer),
                "signal_variants": len(signal),
                "matched_variants": len(matches),
                "representation_disagreements": representation,
                "missing_variants": len(missing),
                "extra_variants": len(extra),
                "exact_profile": "true" if exact_profile else "false",
            }
        )

        for reviewer_index in missing:
            reviewer_variant = reviewer[reviewer_index]
            difference_rows.append(
                {
                    "sample_id": sample_id,
                    "validation_case_id": case_id,
                    "difference": "missing",
                    "reviewer_tokens": ";".join(reviewer_variant.tokens),
                    "signal_position": "",
                    "signal_reference": "",
                    "signal_alternate": "",
                    "signal_kind": "",
                }
            )
        for signal_index in extra:
            signal_variant = signal[signal_index]
            difference_rows.append(
                {
                    "sample_id": sample_id,
                    "validation_case_id": case_id,
                    "difference": "extra",
                    "reviewer_tokens": "",
                    "signal_position": signal_variant.position,
                    "signal_reference": signal_variant.reference,
                    "signal_alternate": signal_variant.alternate,
                    "signal_kind": signal_variant.kind,
                }
            )
        for reviewer_index, signal_index, disagreement in matches:
            if not disagreement:
                continue
            reviewer_variant = reviewer[reviewer_index]
            signal_variant = signal[signal_index]
            difference_rows.append(
                {
                    "sample_id": sample_id,
                    "validation_case_id": case_id,
                    "difference": "representation",
                    "reviewer_tokens": ";".join(reviewer_variant.tokens),
                    "signal_position": signal_variant.position,
                    "signal_reference": signal_variant.reference,
                    "signal_alternate": signal_variant.alternate,
                    "signal_kind": signal_variant.kind,
                }
            )

        total_reviewer += len(reviewer)
        total_signal += len(signal)
        total_matched += len(matches)
        total_representation += representation
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
            str(row["reviewer_tokens"]),
            str(row["signal_position"]),
            str(row["signal_reference"]),
            str(row["signal_alternate"]),
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
            "reviewer_variants": total_reviewer,
            "signal_variants": total_signal,
            "proxy_true_positive_variants": total_matched,
            "proxy_false_positive_variants": total_extra,
            "proxy_false_negative_variants": total_missing,
            "representation_disagreements": total_representation,
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
                    "indel_equivalence": (
                        "single-event full-reference sequence equivalence"
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
