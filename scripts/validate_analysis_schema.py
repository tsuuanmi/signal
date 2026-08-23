"""Validate the compact signal.analysis/v5 contract and call mappings.

Checks the Draft 2020-12 schema, the bundled example and optional result files,
positive SNV/INS/DEL shapes, and representative malformed compact records.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, SchemaError, ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "schemas" / "analysis-v5.schema.json"
DEFAULT_EXAMPLE = ROOT / "docs" / "examples" / "analysis-v5.example.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_documents(validator: Draft202012Validator, paths: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in paths:
        try:
            validator.validate(load_json(path))
        except ValidationError as exc:
            errors.append(f"{path}: invalid: {exc.message}")
    return errors


def call_shapes(example: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return valid SNV, insertion, and deletion documents."""
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


def rejected_call_shapes(example: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    snv, insertion, deletion = call_shapes(example)
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

    return [
        ("SNV with no calls", document("SNV", [])),
        ("SNV supporting call without position", document("SNV", [inserted])),
        ("SNV flanking call", document("SNV", [flanking])),
        ("INS with aligned supporting call", document("INS", [supporting])),
        ("INS with only flanking calls", document("INS", [flanking])),
        ("INS supporting call missing quality", document("INS", [missing_evidence])),
        ("DEL supporting call", document("DEL", [supporting])),
        ("DEL flank with verbose evidence", document("DEL", [verbose_flank])),
    ]


def rejected_summary_shapes(
    example: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    """Return malformed compact summaries that the closed schema must reject."""
    missing_metric = copy.deepcopy(example)
    missing_metric["signal_quality"]["noisy_regions"][0].pop("minimum_primary_snr")

    negative_metric = copy.deepcopy(example)
    negative_metric["signal_quality"]["noisy_regions"][0]["minimum_primary_snr"] = -1

    unknown_field = copy.deepcopy(example)
    unknown_field["signal_quality"]["windows"] = []

    removed_section = copy.deepcopy(example)
    removed_section["sequence"] = {"primary": "ACGT"}

    return [
        ("noisy region missing primary SNR", missing_metric),
        ("noisy region with negative primary SNR", negative_metric),
        ("signal quality with removed windows", unknown_field),
        ("document with removed sequence section", removed_section),
    ]


def assert_rejected(
    validator: Draft202012Validator, rejected: list[tuple[str, dict[str, Any]]]
) -> list[str]:
    errors: list[str] = []
    for label, document in rejected:
        try:
            validator.validate(document)
        except ValidationError:
            continue
        errors.append(f"expected {label} to be rejected, but it validated")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the signal.analysis/v5 schema and result documents."
    )
    parser.add_argument(
        "results",
        nargs="*",
        metavar="RESULT",
        help="optional result JSON documents to validate; defaults to the bundled example",
    )
    args = parser.parse_args(argv)

    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)

    errors: list[str] = []
    try:
        validator.check_schema(schema)
    except SchemaError as exc:
        errors.append(
            f"schema {SCHEMA_PATH} is not a valid Draft 2020-12 schema: {exc.message}"
        )

    paths = [Path(path) for path in args.results] or [DEFAULT_EXAMPLE]
    errors.extend(validate_documents(validator, paths))

    example = load_json(DEFAULT_EXAMPLE)
    valid_shapes = call_shapes(example)
    for index, document in enumerate(valid_shapes, start=1):
        try:
            validator.validate(document)
        except ValidationError as exc:
            errors.append(f"valid call shape {index} was rejected: {exc.message}")
    rejected = rejected_call_shapes(example) + rejected_summary_shapes(example)
    errors.extend(assert_rejected(validator, rejected))

    for error in errors:
        print(f"FAIL: {error}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} check(s) failed", file=sys.stderr)
        return 1
    print(
        f"OK: validated {len(paths)} document(s), {len(valid_shapes)} call shapes; "
        f"rejected {len(rejected)} invalid contract shape(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
