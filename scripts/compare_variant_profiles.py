#!/usr/bin/env python3
"""Compare Signal sample variant profiles with reviewer-derived proxy ground truth."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from validation_corpus.variant_profile import (
    compare_profiles,
    file_sha256,
    load_ground_truth,
    load_reference,
    load_signal_variants,
    parse_reviewer_variants,
    sequence_sha256,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "signal.validation_variant_profile_evaluation/v1"


def resolved(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def write_csv(path: Path, rows: list[dict[str, object]], columns: tuple[str, ...]) -> None:
    with path.open("x", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        target.flush()
        os.fsync(target.fileno())


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser(description=__doc__)
    built.add_argument(
        "--ground-truth",
        type=Path,
        default=Path("data/validation/ground-truth/reviewer-variant-ground-truth.json"),
        help="reviewer-derived proxy ground-truth JSON",
    )
    built.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="Signal sample-result root containing <case>/<case>.json",
    )
    built.add_argument(
        "--reference",
        type=Path,
        default=Path("references/rCRS.fasta"),
        help="reference FASTA used by Signal results",
    )
    built.add_argument(
        "--output-dir",
        type=Path,
        default=Path("validation-results/variant-profile/baseline"),
        help="new no-overwrite evaluation directory",
    )
    return built


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    truth_path = resolved(args.ground_truth)
    results_dir = resolved(args.results_dir)
    reference_path = resolved(args.reference)
    output_dir = resolved(args.output_dir)

    if not truth_path.is_file():
        print(f"error: ground truth is not a regular file: {truth_path}", file=sys.stderr)
        return 1
    if not results_dir.is_dir():
        print(f"error: results directory does not exist: {results_dir}", file=sys.stderr)
        return 1
    if not reference_path.is_file():
        print(f"error: reference is not a regular file: {reference_path}", file=sys.stderr)
        return 1
    if output_dir.exists() or output_dir.is_symlink():
        print(f"error: output directory already exists: {output_dir}", file=sys.stderr)
        return 1

    try:
        truth = load_ground_truth(truth_path)
        reference_name, reference = load_reference(reference_path)
        sample_rows: list[dict[str, object]] = []
        difference_rows: list[dict[str, object]] = []
        summary = {
            "samples": 0,
            "reviewer_variants": 0,
            "signal_variants": 0,
            "matched_variants": 0,
            "representation_disagreements": 0,
            "missing_variants": 0,
            "extra_variants": 0,
            "exact_profiles": 0,
        }

        for record in truth["records"]:
            case_id = record["validation_case_id"]
            sample_path = results_dir / case_id / f"{case_id}.json"
            if not sample_path.is_file():
                raise ValueError(f"missing sample result: {sample_path}")

            reviewer = parse_reviewer_variants(record["variants"], reference)
            signal = load_signal_variants(sample_path, reference_name, reference)
            comparison = compare_profiles(reviewer, signal, reference)
            exact_profile = not comparison.missing and not comparison.extra

            sample_rows.append(
                {
                    "validation_case_id": case_id,
                    "reviewer_variants": len(reviewer),
                    "signal_variants": len(signal),
                    "matched_variants": comparison.matched,
                    "representation_disagreements": len(
                        comparison.representation_disagreements
                    ),
                    "missing_variants": len(comparison.missing),
                    "extra_variants": len(comparison.extra),
                    "exact_profile": "true" if exact_profile else "false",
                }
            )

            for event in comparison.missing:
                difference_rows.append(
                    {
                        "validation_case_id": case_id,
                        "difference": "missing",
                        "reviewer_tokens": ";".join(event.tokens),
                        "signal_position": "",
                        "signal_reference": "",
                        "signal_alternate": "",
                        "signal_kind": "",
                    }
                )
            for event in comparison.extra:
                difference_rows.append(
                    {
                        "validation_case_id": case_id,
                        "difference": "extra",
                        "reviewer_tokens": "",
                        "signal_position": event.position,
                        "signal_reference": event.reference,
                        "signal_alternate": event.alternate,
                        "signal_kind": event.kind,
                    }
                )
            for reviewer_event, signal_event in comparison.representation_disagreements:
                difference_rows.append(
                    {
                        "validation_case_id": case_id,
                        "difference": "representation",
                        "reviewer_tokens": ";".join(reviewer_event.tokens),
                        "signal_position": signal_event.position,
                        "signal_reference": signal_event.reference,
                        "signal_alternate": signal_event.alternate,
                        "signal_kind": signal_event.kind,
                    }
                )

            summary["samples"] += 1
            summary["reviewer_variants"] += len(reviewer)
            summary["signal_variants"] += len(signal)
            summary["matched_variants"] += comparison.matched
            summary["representation_disagreements"] += len(
                comparison.representation_disagreements
            )
            summary["missing_variants"] += len(comparison.missing)
            summary["extra_variants"] += len(comparison.extra)
            summary["exact_profiles"] += int(exact_profile)

        output_dir.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(
            tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent)
        )
        try:
            sample_columns = (
                "validation_case_id",
                "reviewer_variants",
                "signal_variants",
                "matched_variants",
                "representation_disagreements",
                "missing_variants",
                "extra_variants",
                "exact_profile",
            )
            difference_columns = (
                "validation_case_id",
                "difference",
                "reviewer_tokens",
                "signal_position",
                "signal_reference",
                "signal_alternate",
                "signal_kind",
            )
            samples_path = stage / "samples.csv"
            differences_path = stage / "differences.csv"
            write_csv(samples_path, sample_rows, sample_columns)
            write_csv(differences_path, difference_rows, difference_columns)

            index = {
                "schema_version": SCHEMA_VERSION,
                "truth_status": "reviewer_derived_proxy",
                "source_ground_truth_sha256": file_sha256(truth_path),
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
                    "phase_or_locus_special_cases": "none",
                    "true_negative_counting": (
                        "not reported without an explicit callable reviewer-negative domain"
                    ),
                },
                "summary": summary,
                "samples_file": "samples.csv",
                "samples_sha256": file_sha256(samples_path),
                "samples_rows": len(sample_rows),
                "differences_file": "differences.csv",
                "differences_sha256": file_sha256(differences_path),
                "differences_rows": len(difference_rows),
            }
            (stage / "index.json").write_text(
                json.dumps(index, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            sync_directory(stage)
            output_dir.mkdir()
            for name in ("samples.csv", "differences.csv", "index.json"):
                os.rename(stage / name, output_dir / name)
            sync_directory(output_dir)
            sync_directory(output_dir.parent)
        finally:
            shutil.rmtree(stage, ignore_errors=True)
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"OK variant-profile evaluation: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
