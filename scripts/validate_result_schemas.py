"""Validate Signal analysis, basecall, and sample-evidence result contracts."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, SchemaError, ValidationError

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_SCHEMA = ROOT / "docs" / "schemas" / "analysis-v6.schema.json"
ANALYSIS_EXAMPLE = ROOT / "docs" / "examples" / "analysis-v6.example.json"
BASECALL_SCHEMA = ROOT / "docs" / "schemas" / "basecalls-v1.schema.json"
BASECALL_EXAMPLE = ROOT / "docs" / "examples" / "basecalls-v1.example.json"
SAMPLE_SCHEMA = ROOT / "docs" / "schemas" / "sample-evidence-v4.schema.json"
SAMPLE_EXAMPLE = ROOT / "docs" / "examples" / "sample-evidence-v4.example.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validator(path: Path, errors: list[str]) -> Draft202012Validator:
    schema = load_json(path)
    built = Draft202012Validator(schema)
    try:
        built.check_schema(schema)
    except SchemaError as exc:
        errors.append(f"schema {path} is not valid Draft 2020-12: {exc.message}")
    return built


def validate_documents(
    built: Draft202012Validator, paths: list[Path], errors: list[str]
) -> None:
    for path in paths:
        try:
            built.validate(load_json(path))
        except ValidationError as exc:
            errors.append(f"{path}: invalid: {exc.message}")


def analysis_call_shapes(example: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return valid SNV, insertion, and deletion analysis documents."""
    snv = copy.deepcopy(example)
    supporting = copy.deepcopy(snv["variants"][0]["calls"][0])
    flanking = copy.deepcopy(supporting)
    flanking["role"] = "flanking"
    flanking["base"] = "A"

    insertion = copy.deepcopy(example)
    insertion["variants"][0].update(
        {
            "reference": "A",
            "alternate": "AG",
            "kind": "INS",
            "calls": [flanking, supporting],
        }
    )
    deletion = copy.deepcopy(example)
    deletion["variants"][0].update(
        {"reference": "AG", "alternate": "A", "kind": "DEL", "calls": [flanking]}
    )
    return snv, insertion, deletion


def rejected_analysis_shapes(
    example: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    snv, _, deletion = analysis_call_shapes(example)
    supporting = copy.deepcopy(snv["variants"][0]["calls"][0])
    flanking = copy.deepcopy(deletion["variants"][0]["calls"][0])

    def document(kind: str, calls: list[dict[str, Any]]) -> dict[str, Any]:
        built = copy.deepcopy(example)
        built["variants"][0]["kind"] = kind
        built["variants"][0]["calls"] = calls
        return built

    missing_peaks = copy.deepcopy(supporting)
    missing_peaks.pop("peaks")
    missing_quality = copy.deepcopy(supporting)
    missing_quality.pop("quality")
    legacy_pointer = copy.deepcopy(supporting)
    legacy_pointer["ploc"] = 123
    missing_metric = copy.deepcopy(example)
    missing_metric["signal_quality"]["noisy_regions"][0].pop("minimum_primary_snr")
    negative_metric = copy.deepcopy(example)
    negative_metric["signal_quality"]["noisy_regions"][0]["minimum_primary_snr"] = -1
    unknown_field = copy.deepcopy(example)
    unknown_field["signal_quality"]["windows"] = []
    removed_section = copy.deepcopy(example)
    removed_section["sequence"] = {"primary": "ACGT"}
    removed_software_version = copy.deepcopy(example)
    removed_software_version["provenance"]["software_version"] = "0.1.0"

    return [
        ("SNV with no calls", document("SNV", [])),
        ("SNV flanking call", document("SNV", [flanking])),
        ("INS with only flanking calls", document("INS", [flanking])),
        ("DEL supporting call", document("DEL", [supporting])),
        ("variant call without peaks", document("SNV", [missing_peaks])),
        ("variant call without quality", document("SNV", [missing_quality])),
        ("variant call with legacy pointer", document("SNV", [legacy_pointer])),
        ("noisy region missing primary SNR", missing_metric),
        ("noisy region with negative primary SNR", negative_metric),
        ("signal quality with removed windows", unknown_field),
        ("document with removed sequence section", removed_section),
        ("analysis provenance with removed software version", removed_software_version),
    ]


def rejected_basecall_shapes(
    example: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    invalid_primary = copy.deepcopy(example)
    invalid_primary["read"]["primary"] = "ACGTX"
    empty_retained = copy.deepcopy(example)
    empty_retained["read"]["retained"] = ""
    negative_trim = copy.deepcopy(example)
    negative_trim["read"]["trim"]["start"] = -1
    unknown_field = copy.deepcopy(example)
    unknown_field["read"]["relative_quality"] = []
    reference = copy.deepcopy(example)
    reference["provenance"]["reference"] = {"name": "unexpected"}
    software_version = copy.deepcopy(example)
    software_version["provenance"]["software_version"] = "0.1.0"
    return [
        ("basecall primary with unsupported symbol", invalid_primary),
        ("basecall empty retained sequence", empty_retained),
        ("basecall negative trim start", negative_trim),
        ("basecall read with unknown field", unknown_field),
        ("basecall provenance with reference", reference),
        ("basecall provenance with software version", software_version),
    ]


def rejected_sample_shapes(
    example: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    missing_reads = copy.deepcopy(example)
    missing_reads["reads"] = []

    missing_overlaps = copy.deepcopy(example)
    missing_overlaps.pop("overlaps")

    eligible_overlap_with_reason = copy.deepcopy(example)
    eligible_overlap_with_reason["overlaps"][0]["exclusion_reasons"] = [
        "overlap_below_minimum"
    ]

    ineligible_overlap_without_reason = copy.deepcopy(example)
    ineligible_overlap_without_reason["overlaps"][0]["eligible"] = False

    invalid_overlap_agreement = copy.deepcopy(example)
    invalid_overlap_agreement["overlaps"][0]["agreement"] = 1.1

    missing_overlap_agreement = copy.deepcopy(example)
    missing_overlap_agreement["overlaps"][0].pop("agreement")

    zero_comparable_with_agreement = copy.deepcopy(example)
    zero_comparable_with_agreement["overlaps"][0]["comparable_bases"] = 0
    zero_comparable_with_agreement["overlaps"][0]["agreements"] = 0
    zero_comparable_with_agreement["overlaps"][0]["conflicts"] = 0

    old_sample_schema = copy.deepcopy(example)
    old_sample_schema["schema_version"] = "signal.sample_evidence/v3"

    invalid_sample_id = copy.deepcopy(example)
    invalid_sample_id["sample_id"] = "../sample"

    all_reference_locus = copy.deepcopy(example)
    for observation in all_reference_locus["locus_differences"][0]["observations"]:
        observation["state"] = "reference"
        observation["base"] = all_reference_locus["locus_differences"][0]["reference"]

    verbose_deletion = copy.deepcopy(example)
    observation = verbose_deletion["locus_differences"][0]["observations"][0]
    observation["state"] = "deletion"

    empty_read = copy.deepcopy(example)
    empty_read["variants"][0]["support"][0]["read"] = ""

    repeated_identity = copy.deepcopy(example)
    repeated_identity["variants"][0]["support"][0]["read_name"] = "legacy.ab1"

    legacy_loci = copy.deepcopy(example)
    legacy_loci["loci"] = []
    legacy_loci.pop("locus_differences")

    unknown_field = copy.deepcopy(example)
    unknown_field["consensus"] = "ACGT"

    empty_support = copy.deepcopy(example)
    empty_support["variants"][0]["support"] = []

    eligible_with_reason = copy.deepcopy(example)
    eligible_with_reason["variants"][0]["support"][0]["exclusion_reasons"] = [
        "peak_below_minimum"
    ]

    ineligible_without_reason = copy.deepcopy(example)
    ineligible_without_reason["variants"][0]["support"][0]["eligible"] = False

    missing_call_peaks = copy.deepcopy(example)
    missing_call_peaks["variants"][0]["support"][0]["calls"][0].pop("peaks")

    empty_variant_calls = copy.deepcopy(example)
    empty_variant_calls["variants"][0]["support"][0]["calls"] = []

    unknown_exclusion_reason = copy.deepcopy(example)
    unknown_exclusion_reason["variants"][0]["support"][0]["eligible"] = False
    unknown_exclusion_reason["variants"][0]["support"][0]["exclusion_reasons"] = [
        "unsupported_reason"
    ]

    return [
        ("sample evidence with no reads", missing_reads),
        ("sample evidence without overlap graph", missing_overlaps),
        (
            "eligible overlap with exclusion reason",
            eligible_overlap_with_reason,
        ),
        (
            "ineligible overlap without exclusion reason",
            ineligible_overlap_without_reason,
        ),
        ("overlap agreement above one", invalid_overlap_agreement),
        ("overlap with comparable bases but no agreement", missing_overlap_agreement),
        ("zero-comparable overlap with agreement", zero_comparable_with_agreement),
        ("sample evidence using old schema version", old_sample_schema),
        ("sample evidence with invalid sample id", invalid_sample_id),
        (
            "sparse difference locus with only reference observations",
            all_reference_locus,
        ),
        ("deletion difference carrying called-base fields", verbose_deletion),
        ("sample evidence with empty read reference", empty_read),
        ("sample support with repeated read identity", repeated_identity),
        ("sample evidence using removed loci field", legacy_loci),
        ("sample evidence with consensus field", unknown_field),
        ("sample variant with no supporting reads", empty_support),
        ("eligible sample variant support with exclusion reason", eligible_with_reason),
        (
            "ineligible sample variant support without exclusion reason",
            ineligible_without_reason,
        ),
        ("sample variant call without peaks", missing_call_peaks),
        ("sample variant support without mapped calls", empty_variant_calls),
        (
            "sample variant support with unknown exclusion reason",
            unknown_exclusion_reason,
        ),
    ]


def assert_rejected(
    built: Draft202012Validator,
    rejected: list[tuple[str, dict[str, Any]]],
    errors: list[str],
) -> None:
    for label, document in rejected:
        try:
            built.validate(document)
        except ValidationError:
            continue
        errors.append(f"expected {label} to be rejected, but it validated")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--analysis",
        action="append",
        type=Path,
        default=[],
        metavar="RESULT",
        help="analysis result to validate; may be repeated",
    )
    parser.add_argument(
        "--basecalls",
        action="append",
        type=Path,
        default=[],
        metavar="RESULT",
        help="basecall result to validate; may be repeated",
    )
    parser.add_argument(
        "--sample-evidence",
        action="append",
        type=Path,
        default=[],
        metavar="RESULT",
        help="sample-evidence result to validate; may be repeated",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    errors: list[str] = []
    analysis_validator = validator(ANALYSIS_SCHEMA, errors)
    basecall_validator = validator(BASECALL_SCHEMA, errors)
    sample_validator = validator(SAMPLE_SCHEMA, errors)
    analysis_paths = args.analysis or [ANALYSIS_EXAMPLE]
    basecall_paths = args.basecalls or [BASECALL_EXAMPLE]
    sample_paths = args.sample_evidence or [SAMPLE_EXAMPLE]
    validate_documents(analysis_validator, analysis_paths, errors)
    validate_documents(basecall_validator, basecall_paths, errors)
    validate_documents(sample_validator, sample_paths, errors)

    analysis_example = load_json(ANALYSIS_EXAMPLE)
    valid_shapes = analysis_call_shapes(analysis_example)
    for index, document in enumerate(valid_shapes, start=1):
        try:
            analysis_validator.validate(document)
        except ValidationError as exc:
            errors.append(
                f"valid analysis call shape {index} was rejected: {exc.message}"
            )
    rejected_analysis = rejected_analysis_shapes(analysis_example)
    rejected_basecalls = rejected_basecall_shapes(load_json(BASECALL_EXAMPLE))
    rejected_samples = rejected_sample_shapes(load_json(SAMPLE_EXAMPLE))
    assert_rejected(analysis_validator, rejected_analysis, errors)
    assert_rejected(basecall_validator, rejected_basecalls, errors)
    assert_rejected(sample_validator, rejected_samples, errors)

    for error in errors:
        print(f"FAIL: {error}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} check(s) failed", file=sys.stderr)
        return 1
    print(
        f"OK: validated {len(analysis_paths)} analysis, {len(basecall_paths)} basecall, "
        f"and {len(sample_paths)} sample-evidence document(s), {len(valid_shapes)} "
        f"analysis call shapes; rejected "
        f"{len(rejected_analysis) + len(rejected_basecalls) + len(rejected_samples)} "
        "invalid shape(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
