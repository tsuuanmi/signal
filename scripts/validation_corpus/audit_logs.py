"""Strict parsing of validation operational logs into read-level audit metrics."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from .audit_analysis import RawReadAudit
from .research_model import ResearchCorpus

REQUIRED_READ_EVENTS = (
    "basecalling_completed",
    "signal_processing_completed",
    "quality_control_completed",
    "alignment_completed",
    "warning_summary",
)


def event_fields(line: str, label: str) -> dict[str, str] | None:
    marker = " - "
    if marker not in line:
        return None
    payload = line.split(marker, 1)[1]
    tokens = shlex.split(payload)
    fields: dict[str, str] = {}
    for token in tokens:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        if key in fields:
            raise ValueError(f"{label}: duplicate log field {key!r}")
        fields[key] = value
    if "event" not in fields:
        return None
    return fields


def required_int(fields: dict[str, str], key: str, label: str) -> int:
    raw = fields.get(key)
    if raw is None:
        raise ValueError(f"{label}: missing integer field {key}")
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"{label}: invalid integer field {key}={raw!r}") from error
    return value


def required_float(fields: dict[str, str], key: str, label: str) -> float:
    raw = fields.get(key)
    if raw is None:
        raise ValueError(f"{label}: missing numeric field {key}")
    try:
        value = float(raw)
    except ValueError as error:
        raise ValueError(f"{label}: invalid numeric field {key}={raw!r}") from error
    return value


def trim_bounds(fields: dict[str, str], label: str) -> tuple[int, int]:
    raw = fields.get("trim")
    if raw is None or ".." not in raw:
        raise ValueError(f"{label}: invalid trim field {raw!r}")
    start_text, end_text = raw.split("..", 1)
    try:
        start = int(start_text)
        end = int(end_text)
    except ValueError as error:
        raise ValueError(f"{label}: invalid trim field {raw!r}") from error
    if start < 0 or end <= start:
        raise ValueError(f"{label}: invalid trim bounds {raw!r}")
    return start, end


def normalized_orientation(value: str, label: str) -> str:
    lowered = value.lower()
    if lowered not in {"forward", "reverse"}:
        raise ValueError(f"{label}: unsupported orientation {value!r}")
    return lowered


def parse_case_log(
    path: Path,
    case_id: str,
    expected_reads: dict[str, dict[str, Any]],
) -> list[RawReadAudit]:
    """Parse one validation log and require one complete record per corpus read."""
    if not path.is_file():
        raise ValueError(f"validation log is not a regular file: {path}")

    records: list[RawReadAudit] = []
    seen_reads: set[str] = set()
    active_sha256: str | None = None
    active_fields: dict[str, dict[str, str]] = {}

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        label = f"{path}:{line_number}"
        fields = event_fields(line, label)
        if fields is None:
            continue
        event = fields["event"]

        if event == "sample_read_started":
            if active_sha256 is not None:
                raise ValueError(f"{label}: previous read did not complete")
            read_sha256 = fields.get("trace_sha256")
            if read_sha256 is None or read_sha256 not in expected_reads:
                raise ValueError(f"{label}: unexpected trace SHA-256 {read_sha256!r}")
            if read_sha256 in seen_reads:
                raise ValueError(f"{label}: duplicate read {read_sha256}")
            active_sha256 = read_sha256
            active_fields = {}
            continue

        if active_sha256 is None:
            continue

        if event in REQUIRED_READ_EVENTS:
            if event in active_fields:
                raise ValueError(f"{label}: duplicate event {event}")
            active_fields[event] = fields
            continue

        if event != "sample_read_completed":
            continue

        completed_sha256 = fields.get("trace_sha256")
        if completed_sha256 != active_sha256:
            raise ValueError(
                f"{label}: completed read {completed_sha256!r} does not match "
                f"active read {active_sha256!r}"
            )
        missing = [
            event_name
            for event_name in REQUIRED_READ_EVENTS
            if event_name not in active_fields
        ]
        if missing:
            raise ValueError(
                f"{label}: incomplete read log for {active_sha256}: "
                f"missing {', '.join(missing)}"
            )

        basecalling = active_fields["basecalling_completed"]
        signal = active_fields["signal_processing_completed"]
        quality = active_fields["quality_control_completed"]
        alignment = active_fields["alignment_completed"]
        warning = active_fields["warning_summary"]
        start, end = trim_bounds(quality, label)
        inferred_orientation = normalized_orientation(
            alignment.get("orientation", ""), label
        )
        completed_orientation = normalized_orientation(
            fields.get("orientation", ""), label
        )
        if completed_orientation != inferred_orientation:
            raise ValueError(
                f"{label}: alignment/completion orientation disagreement for "
                f"{active_sha256}"
            )

        read = expected_reads[active_sha256]
        records.append(
            RawReadAudit(
                validation_case_id=case_id,
                read_sha256=active_sha256,
                sequencing_run_id=read["sequencing_run_id"],
                amplicon_id=read["amplicon_id"],
                declared_direction=read["declared_direction"],
                inferred_orientation=inferred_orientation,
                calls=required_int(basecalling, "calls", label),
                profiled_loci=required_int(signal, "profiled_loci", label),
                noisy_calls=required_int(signal, "noisy_calls", label),
                trim_start_0based=start,
                trim_end_0based_exclusive=end,
                retained=required_int(quality, "retained", label),
                retained_fraction=required_float(quality, "retained_fraction", label),
                callable_columns=required_int(alignment, "callable_columns", label),
                callable_identity=required_float(alignment, "callable_identity", label),
                mismatches=required_int(alignment, "mismatches", label),
                gap_opens=required_int(alignment, "gap_opens", label),
                excluded_variant_candidates=required_int(
                    warning, "excluded_variant_candidates", label
                ),
            )
        )
        seen_reads.add(active_sha256)
        active_sha256 = None
        active_fields = {}

    if active_sha256 is not None:
        raise ValueError(f"{path}: final read did not complete")
    missing_reads = set(expected_reads) - seen_reads
    if missing_reads:
        raise ValueError(
            f"{path}: missing {len(missing_reads)} corpus read(s) from validation log"
        )
    return records


def load_read_audits(corpus: ResearchCorpus, corpus_dir: Path) -> list[RawReadAudit]:
    """Load all case logs in corpus order and bind them to corpus read metadata."""
    logs_dir = corpus_dir.resolve() / "logs"
    if not logs_dir.is_dir():
        raise ValueError(f"validation logs directory does not exist: {logs_dir}")

    records: list[RawReadAudit] = []
    for case in corpus.cases:
        case_id = case.metadata["validation_case_id"]
        records.extend(
            parse_case_log(
                logs_dir / f"{case_id}.validation.log",
                case_id,
                case.reads,
            )
        )
    return records
