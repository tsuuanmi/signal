"""Validate Signal's analysis and reference-free basecall result contracts."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, SchemaError, ValidationError

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_SCHEMA = ROOT / "docs" / "schemas" / "analysis-v5.schema.json"
ANALYSIS_EXAMPLE = ROOT / "docs" / "examples" / "analysis-v5.example.json"
BASECALL_SCHEMA = ROOT / "docs" / "schemas" / "basecalls-v1.schema.json"
BASECALL_EXAMPLE = ROOT / "docs" / "examples" / "basecalls-v1.example.json"


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
    inserted = copy.deepcopy(supporting)
    inserted.pop("position")
    flanking = copy.deepcopy(supporting)
    flanking["role"] = "flanking"
    flanking.pop("maximum_peak_height")
    flanking.pop("relative_quality")

    insertion = copy.deepcopy(example)
    insertion["variants"][0].update(
        {
            "reference": "A",
            "alternate": "AG",
            "kind": "INS",
            "calls": [flanking, inserted],
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
    snv, insertion, deletion = analysis_call_shapes(example)
    supporting = copy.deepcopy(snv["variants"][0]["calls"][0])
    inserted = copy.deepcopy(insertion["variants"][0]["calls"][1])
    flanking = copy.deepcopy(deletion["variants"][0]["calls"][0])

    def document(kind: str, calls: list[dict[str, Any]]) -> dict[str, Any]:
        built = copy.deepcopy(example)
        built["variants"][0]["kind"] = kind
        built["variants"][0]["calls"] = calls
        return built

    missing_evidence = copy.deepcopy(inserted)
    missing_evidence.pop("relative_quality")
    verbose_flank = copy.deepcopy(flanking)
    verbose_flank["maximum_peak_height"] = 800
    missing_metric = copy.deepcopy(example)
    missing_metric["signal_quality"]["noisy_regions"][0].pop("minimum_primary_snr")
    negative_metric = copy.deepcopy(example)
    negative_metric["signal_quality"]["noisy_regions"][0]["minimum_primary_snr"] = -1
    unknown_field = copy.deepcopy(example)
    unknown_field["signal_quality"]["windows"] = []
    removed_section = copy.deepcopy(example)
    removed_section["sequence"] = {"primary": "ACGT"}

    return [
        ("SNV with no calls", document("SNV", [])),
        ("SNV supporting call without position", document("SNV", [inserted])),
        ("SNV flanking call", document("SNV", [flanking])),
        ("INS with aligned supporting call", document("INS", [supporting])),
        ("INS with only flanking calls", document("INS", [flanking])),
        ("INS supporting call missing quality", document("INS", [missing_evidence])),
        ("DEL supporting call", document("DEL", [supporting])),
        ("DEL flank with verbose evidence", document("DEL", [verbose_flank])),
        ("noisy region missing primary SNR", missing_metric),
        ("noisy region with negative primary SNR", negative_metric),
        ("signal quality with removed windows", unknown_field),
        ("document with removed sequence section", removed_section),
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
    return [
        ("basecall primary with unsupported symbol", invalid_primary),
        ("basecall empty retained sequence", empty_retained),
        ("basecall negative trim start", negative_trim),
        ("basecall read with unknown field", unknown_field),
        ("basecall provenance with reference", reference),
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    errors: list[str] = []
    analysis_validator = validator(ANALYSIS_SCHEMA, errors)
    basecall_validator = validator(BASECALL_SCHEMA, errors)
    analysis_paths = args.analysis or [ANALYSIS_EXAMPLE]
    basecall_paths = args.basecalls or [BASECALL_EXAMPLE]
    validate_documents(analysis_validator, analysis_paths, errors)
    validate_documents(basecall_validator, basecall_paths, errors)

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
    assert_rejected(analysis_validator, rejected_analysis, errors)
    assert_rejected(basecall_validator, rejected_basecalls, errors)

    for error in errors:
        print(f"FAIL: {error}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} check(s) failed", file=sys.stderr)
        return 1
    print(
        f"OK: validated {len(analysis_paths)} analysis and {len(basecall_paths)} basecall "
        f"document(s), {len(valid_shapes)} analysis call shapes; rejected "
        f"{len(rejected_analysis) + len(rejected_basecalls)} invalid shape(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
