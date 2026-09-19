"""Strict local validation-corpus manifest parsing and trace provenance checks."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from .filesystem import file_sha256
from .model import (
    CASE_COLUMNS,
    MANIFEST_COLUMNS,
    CaseMetadata,
    TraceRecord,
    ValidationCase,
)

CASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def optional_text(value: str) -> str | None:
    value = value.strip()
    return value or None


def required_text(row: dict[str, str], column: str, line: int) -> str:
    value = row[column].strip()
    if not value:
        raise ValueError(f"manifest line {line}: {column} is required")
    return value


def parse_bool(value: str, column: str, line: int) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"manifest line {line}: {column} must be true or false")


def parse_optional_fraction(value: str, line: int) -> float | None:
    value = value.strip()
    if not value:
        return None
    try:
        parsed = float(value)
    except ValueError as error:
        raise ValueError(
            f"manifest line {line}: known_mixture_fraction must be numeric"
        ) from error
    if not 0.0 <= parsed <= 1.0:
        raise ValueError(
            f"manifest line {line}: known_mixture_fraction must be within [0, 1]"
        )
    return parsed


def parse_optional_locus(value: str, line: int) -> int | None:
    value = value.strip()
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(
            f"manifest line {line}: truth_locus must be an integer"
        ) from error
    if parsed < 1:
        raise ValueError(f"manifest line {line}: truth_locus must be at least 1")
    return parsed


def parse_tags(value: str) -> tuple[str, ...]:
    tags = [tag.strip() for tag in value.split(";") if tag.strip()]
    return tuple(dict.fromkeys(tags))


def normalized_row(row: dict[str, str | None]) -> dict[str, str]:
    return {column: (row.get(column) or "").strip() for column in MANIFEST_COLUMNS}


def trace_path(manifest: Path, raw_path: str, line: int) -> Path:
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = manifest.parent / candidate
    if candidate.is_symlink():
        raise ValueError(f"manifest line {line}: refusing symlinked trace: {candidate}")
    resolved = candidate.resolve()
    if not resolved.is_file():
        raise ValueError(
            f"manifest line {line}: trace_path is not a regular file: {resolved}"
        )
    return resolved


def case_metadata(row: dict[str, str], line: int) -> CaseMetadata:
    case_id = required_text(row, "validation_case_id", line)
    if CASE_ID.fullmatch(case_id) is None:
        raise ValueError(
            f"manifest line {line}: invalid validation_case_id {case_id!r}"
        )
    return CaseMetadata(
        validation_case_id=case_id,
        source_group_id=required_text(row, "source_group_id", line),
        specimen_group_id=optional_text(row["specimen_group_id"]),
        truth_class=required_text(row, "truth_class", line),
        truth_method=required_text(row, "truth_method", line),
        truth_locus=parse_optional_locus(row["truth_locus"], line),
        truth_reference=optional_text(row["truth_reference"]),
        truth_alternate=optional_text(row["truth_alternate"]),
        known_mixture_fraction=parse_optional_fraction(
            row["known_mixture_fraction"], line
        ),
        include_in_threshold_fit=parse_bool(
            row["include_in_threshold_fit"], "include_in_threshold_fit", line
        ),
        holdout_group=required_text(row, "holdout_group", line),
        approval_record=required_text(row, "approval_record", line),
        redistribution_status=required_text(row, "redistribution_status", line),
        notes=optional_text(row["notes"]),
    )


def trace_record(manifest: Path, row: dict[str, str], line: int) -> TraceRecord:
    raw_path = required_text(row, "trace_path", line)
    expected_sha256 = required_text(row, "trace_sha256", line)
    if SHA256.fullmatch(expected_sha256) is None:
        raise ValueError(
            f"manifest line {line}: trace_sha256 must be 64 lowercase hex characters"
        )
    path = trace_path(manifest, raw_path, line)
    actual_sha256 = file_sha256(path)
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"manifest line {line}: trace SHA-256 mismatch for {path.name}: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )
    direction = optional_text(row["declared_direction"])
    if direction not in {None, "forward", "reverse"}:
        raise ValueError(
            f"manifest line {line}: declared_direction must be forward, reverse, "
            "or empty"
        )
    return TraceRecord(
        path=path,
        trace_sha256=expected_sha256,
        pcr_replicate_id=optional_text(row["pcr_replicate_id"]),
        sequencing_run_id=optional_text(row["sequencing_run_id"]),
        instrument_id=optional_text(row["instrument_id"]),
        amplicon_id=optional_text(row["amplicon_id"]),
        declared_direction=direction,
        artifact_tags=parse_tags(row["artifact_tags"]),
    )


def load_manifest(path: Path) -> list[ValidationCase]:
    """Validate all rows and group one-trace records by validation case."""
    manifest = path.resolve()
    if not manifest.is_file():
        raise ValueError(f"manifest is not a regular file: {manifest}")

    cases: dict[str, ValidationCase] = {}
    trace_owners: dict[str, str] = {}
    with manifest.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames
        if fieldnames is None:
            raise ValueError("manifest has no header")
        missing = sorted(set(MANIFEST_COLUMNS) - set(fieldnames))
        extra = sorted(set(fieldnames) - set(MANIFEST_COLUMNS))
        duplicates = len(fieldnames) != len(set(fieldnames))
        if missing or extra or duplicates or len(fieldnames) != len(MANIFEST_COLUMNS):
            details = []
            if missing:
                details.append(f"missing columns: {', '.join(missing)}")
            if extra:
                details.append(f"unexpected columns: {', '.join(extra)}")
            if duplicates:
                details.append("duplicate column names")
            raise ValueError("invalid manifest header: " + "; ".join(details))

        for line, raw in enumerate(reader, start=2):
            row = normalized_row(raw)
            if not any(row.values()):
                continue
            metadata = case_metadata(row, line)
            trace = trace_record(manifest, row, line)
            owner = trace_owners.get(trace.trace_sha256)
            if owner is not None:
                raise ValueError(
                    f"manifest line {line}: trace SHA-256 already belongs to {owner}"
                )
            trace_owners[trace.trace_sha256] = metadata.validation_case_id

            current = cases.get(metadata.validation_case_id)
            if current is None:
                cases[metadata.validation_case_id] = ValidationCase(metadata, [trace])
                continue
            if current.metadata != metadata:
                differing = [
                    column
                    for column in CASE_COLUMNS
                    if getattr(current.metadata, column) != getattr(metadata, column)
                ]
                raise ValueError(
                    f"manifest line {line}: case-level metadata changed within "
                    f"{metadata.validation_case_id}: {', '.join(differing)}"
                )
            current.traces.append(trace)

    if not cases:
        raise ValueError("manifest contains no validation cases")

    source_holdouts: dict[str, str] = {}
    for case in cases.values():
        source_group = case.metadata.source_group_id
        holdout_group = case.metadata.holdout_group
        previous = source_holdouts.setdefault(source_group, holdout_group)
        if previous != holdout_group:
            raise ValueError(
                f"source_group_id {source_group!r} spans holdout groups "
                f"{previous!r} and {holdout_group!r}"
            )
    return list(cases.values())


def select_cases(
    cases: list[ValidationCase], requested: list[str] | None, limit: int | None
) -> list[ValidationCase]:
    selected = cases
    if requested:
        if len(requested) != len(set(requested)):
            raise ValueError("--case values must be unique")
        available = {case.metadata.validation_case_id for case in cases}
        missing = [case_id for case_id in requested if case_id not in available]
        if missing:
            raise ValueError(f"unknown validation case: {missing[0]}")
        requested_set = set(requested)
        selected = [
            case
            for case in cases
            if case.metadata.validation_case_id in requested_set
        ]
    if limit is not None:
        if limit < 1:
            raise ValueError("--limit must be at least 1")
        selected = selected[:limit]
    if not selected:
        raise ValueError("no validation cases selected")
    return selected
