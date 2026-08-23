"""Validate signal.analysis/v4 signal windows and variant call mappings.

Checks that the Draft 2020-12 schema is itself valid, that the bundled example
and any supplied result files validate against it, and that malformed signal and
SNV/INS/DEL call-mapping shapes are rejected.

Exit status is non-zero if any check fails.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "schemas" / "analysis-v4.schema.json"
DEFAULT_EXAMPLE = ROOT / "docs" / "examples" / "analysis-v4.example.json"


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


def rejected_call_shapes(example: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Return (label, document) pairs that the root schema must reject.

    Shapes are derived by mutating the example's single SNV supporting call
    into an inserted (no position) and a flanking call.
    """
    base_variant = copy.deepcopy(example["variants"][0])
    supporting = copy.deepcopy(base_variant["calls"][0])

    inserted = copy.deepcopy(supporting)
    inserted.pop("position")

    flanking = copy.deepcopy(supporting)
    flanking["role"] = "flanking"

    def document(kind: str, calls: list[dict[str, Any]]) -> dict[str, Any]:
        built = copy.deepcopy(example)
        built["variants"][0]["kind"] = kind
        built["variants"][0]["calls"] = calls
        return built

    return [
        ("SNV empty calls", document("SNV", [])),
        ("SNV supporting call without position", document("SNV", [inserted])),
        ("SNV flanking call", document("SNV", [flanking])),
        ("INS empty calls", document("INS", [])),
        ("INS aligned supporting call", document("INS", [supporting])),
        ("INS only flanking calls", document("INS", [flanking])),
        ("DEL empty calls", document("DEL", [])),
        ("DEL supporting call without position", document("DEL", [inserted])),
    ]


def rejected_signal_shapes(example: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Return malformed signal summaries that the closed schema must reject."""
    missing_metric = copy.deepcopy(example)
    missing_metric["signal"]["windows"][0].pop("minimum_primary_snr")

    negative_metric = copy.deepcopy(example)
    negative_metric["signal"]["windows"][0]["maximum_secondary_snr"] = -1

    unknown_field = copy.deepcopy(example)
    unknown_field["signal"]["windows"][0]["raw_channels"] = []

    return [
        ("signal window missing primary SNR", missing_metric),
        ("signal window with negative secondary SNR", negative_metric),
        ("signal window with unknown raw channels", unknown_field),
    ]


def assert_rejected(
    validator: Draft202012Validator, rejected: list[tuple[str, dict[str, Any]]]
) -> list[str]:
    errors: list[str] = []
    for label, variant in rejected:
        try:
            validator.validate(variant)
        except ValidationError:
            continue
        errors.append(f"expected {label} to be rejected, but it validated")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the signal.analysis/v4 schema and result documents."
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
    except ValidationError as exc:
        errors.append(
            f"schema {SCHEMA_PATH} is not a valid Draft 2020-12 schema: {exc.message}"
        )

    paths = [Path(p) for p in args.results] or [DEFAULT_EXAMPLE]
    errors.extend(validate_documents(validator, paths))

    example = load_json(DEFAULT_EXAMPLE)
    rejected = rejected_call_shapes(example) + rejected_signal_shapes(example)
    errors.extend(assert_rejected(validator, rejected))

    for error in errors:
        print(f"FAIL: {error}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} check(s) failed", file=sys.stderr)
        return 1
    print(
        f"OK: validated {len(paths)} document(s); rejected {len(rejected)} invalid contract shape(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
