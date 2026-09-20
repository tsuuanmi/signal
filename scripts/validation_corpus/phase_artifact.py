"""Validated I/O contract for post-poly-C phase-hypothesis artifacts."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .filesystem import file_sha256
from .model import PHASE_HYPOTHESIS_SCHEMA_VERSION
from .phase_hypotheses import HYPOTHESIS_COLUMNS, WINDOW_COLUMNS
from .research_loader import json_object, strict_keys

SOURCE_INDEX_FIELDS = (
    "schema_version",
    "source_polyc_phase_sha256",
    "source_corpus_sha256",
    "signal_version",
    "manifest_sha256",
    "reference_sha256",
    "configuration_sha256",
    "method",
    "windows_file",
    "windows_sha256",
    "windows_rows",
    "windows_columns",
    "hypotheses_file",
    "hypotheses_sha256",
    "hypotheses_rows",
    "hypotheses_columns",
)


@dataclass(frozen=True)
class WindowRecord:
    window_id: str
    validation_case_id: str
    read_sha256: str
    tract_id: str
    amplicon_id: str
    orientation: str
    interrupt_aligned_base: str
    start_distance: int
    end_distance: int
    start_call_index: int
    end_call_index: int
    profile_observations: int
    noisy_observations: int
    mean_profile_impurity: float
    mean_zero_reference_mass: float


@dataclass(frozen=True)
class CandidateRecord:
    window_id: str
    offset: int
    informative_positions: int
    zero_mass: float | None
    shifted_mass: float | None
    residual_mass: float | None


def index_count(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def csv_int(value: str, label: str, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{label} must be an integer") from error
    if minimum is not None and parsed < minimum:
        raise ValueError(f"{label} must be >= {minimum}")
    return parsed


def unit_float(value: str, label: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise ValueError(f"{label} must be numeric") from error
    if not math.isfinite(parsed) or parsed < 0.0 or parsed > 1.0:
        raise ValueError(f"{label} must be finite in [0, 1]")
    return parsed


def optional_unit_float(value: str, label: str) -> float | None:
    return None if value == "" else unit_float(value, label)


def source_offsets(method: Any) -> tuple[int, ...]:
    if not isinstance(method, dict):
        raise TypeError("phase-hypothesis method must be an object")
    raw = method.get("candidate_offsets")
    if not isinstance(raw, list) or not raw:
        raise ValueError("phase-hypothesis candidate_offsets must be a non-empty list")
    offsets: list[int] = []
    for index, value in enumerate(raw):
        if not isinstance(value, int) or isinstance(value, bool) or value == 0:
            raise ValueError(f"candidate_offsets[{index}] must be a non-zero integer")
        offsets.append(value)
    if len(offsets) != len(set(offsets)):
        raise ValueError("phase-hypothesis candidate_offsets must be unique")
    return tuple(offsets)


@dataclass(frozen=True)
class PhaseHypothesisParameters:
    window_size: int
    window_step: int
    max_offset: int
    offsets: tuple[int, ...]


PRODUCTION_V1_PARAMETERS = PhaseHypothesisParameters(
    window_size=25,
    window_step=5,
    max_offset=5,
    offsets=tuple(range(-5, 0)) + tuple(range(1, 6)),
)


def method_positive_int(method: dict[str, Any], key: str) -> int:
    value = method.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"phase-hypothesis {key} must be a positive integer")
    return value


def source_parameters(method: Any) -> PhaseHypothesisParameters:
    if not isinstance(method, dict):
        raise TypeError("phase-hypothesis method must be an object")
    window_size = method_positive_int(method, "window_size_profile_observations")
    window_step = method_positive_int(method, "window_step_profile_observations")
    max_offset = method_positive_int(
        method,
        "max_reference_offset_in_read_order",
    )
    offsets = source_offsets(method)
    expected = tuple(range(-max_offset, 0)) + tuple(range(1, max_offset + 1))
    if offsets != expected:
        raise ValueError(
            "phase-hypothesis candidate_offsets differ from max reference offset"
        )
    return PhaseHypothesisParameters(
        window_size=window_size,
        window_step=window_step,
        max_offset=max_offset,
        offsets=offsets,
    )


def production_v1_parameters(method: Any) -> PhaseHypothesisParameters:
    parameters = source_parameters(method)
    if parameters != PRODUCTION_V1_PARAMETERS:
        raise ValueError(
            "phase-hypothesis method does not match signal.polyc_phase/v1 constants"
        )
    return parameters


def validate_source(source_dir: Path) -> tuple[dict[str, Any], tuple[int, ...]]:
    index_path = source_dir / "index.json"
    if not index_path.is_file():
        raise ValueError(f"phase-hypothesis index is not a regular file: {index_path}")
    index = json_object(index_path)
    strict_keys(index, SOURCE_INDEX_FIELDS, "phase-hypothesis index")
    if index["schema_version"] != PHASE_HYPOTHESIS_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported phase-hypothesis schema: {index['schema_version']!r}"
        )

    specs = (
        (
            "windows.csv",
            WINDOW_COLUMNS,
            "windows_file",
            "windows_sha256",
            "windows_rows",
            "windows_columns",
        ),
        (
            "hypotheses.csv",
            HYPOTHESIS_COLUMNS,
            "hypotheses_file",
            "hypotheses_sha256",
            "hypotheses_rows",
            "hypotheses_columns",
        ),
    )
    for filename, columns, file_key, sha_key, rows_key, columns_key in specs:
        if index[file_key] != filename:
            raise ValueError(f"phase-hypothesis {file_key} must be {filename}")
        if index[columns_key] != list(columns):
            raise ValueError(
                f"phase-hypothesis {columns_key} differ from current contract"
            )
        path = source_dir / filename
        if not path.is_file():
            raise ValueError(f"phase-hypothesis table is not a regular file: {path}")
        if index[sha_key] != file_sha256(path):
            raise ValueError(f"{filename} SHA-256 mismatch")
        index_count(index[rows_key], f"phase-hypothesis {rows_key}")
    parameters = source_parameters(index["method"])
    return index, parameters.offsets


def parse_window(row: dict[str, str], line: int) -> WindowRecord:
    label = f"windows.csv:{line}"
    required = ("window_id", "validation_case_id", "read_sha256", "tract_id")
    if any(not row[field] for field in required):
        raise ValueError(f"{label}: missing window/case/read/tract identity")
    orientation = row["orientation"]
    if orientation not in {"forward", "reverse"}:
        raise ValueError(f"{label}.orientation must be forward or reverse")
    interrupt = row["interrupt_aligned_base"]
    if interrupt not in {"", "A", "C", "G", "T"}:
        raise ValueError(f"{label}.interrupt_aligned_base must be A/C/G/T or empty")

    start = csv_int(
        row["start_distance_after_tract"],
        f"{label}.start_distance_after_tract",
        1,
    )
    end = csv_int(
        row["end_distance_after_tract"],
        f"{label}.end_distance_after_tract",
        1,
    )
    if end < start:
        raise ValueError(f"{label}: window end precedes start")
    start_call_index = csv_int(
        row["start_call_index_0based"],
        f"{label}.start_call_index_0based",
        0,
    )
    end_call_index = csv_int(
        row["end_call_index_0based"],
        f"{label}.end_call_index_0based",
        0,
    )
    if end_call_index < start_call_index:
        raise ValueError(f"{label}: window call-index end precedes start")
    profile_count = csv_int(
        row["profile_observations"],
        f"{label}.profile_observations",
        1,
    )
    noisy_count = csv_int(
        row["noisy_observations"],
        f"{label}.noisy_observations",
        0,
    )
    if noisy_count > profile_count:
        raise ValueError(f"{label}: noisy observations exceed profile observations")

    return WindowRecord(
        window_id=row["window_id"],
        validation_case_id=row["validation_case_id"],
        read_sha256=row["read_sha256"],
        tract_id=row["tract_id"],
        amplicon_id=row["amplicon_id"],
        orientation=orientation,
        interrupt_aligned_base=interrupt,
        start_distance=start,
        end_distance=end,
        start_call_index=start_call_index,
        end_call_index=end_call_index,
        profile_observations=profile_count,
        noisy_observations=noisy_count,
        mean_profile_impurity=unit_float(
            row["mean_profile_impurity"],
            f"{label}.mean_profile_impurity",
        ),
        mean_zero_reference_mass=unit_float(
            row["mean_zero_reference_mass"],
            f"{label}.mean_zero_reference_mass",
        ),
    )


def parse_candidate(row: dict[str, str], line: int) -> CandidateRecord:
    label = f"hypotheses.csv:{line}"
    window_id = row["window_id"]
    if not window_id:
        raise ValueError(f"{label}.window_id must be non-empty")
    offset = csv_int(
        row["reference_offset_in_read_order"],
        f"{label}.reference_offset_in_read_order",
    )
    if offset == 0:
        raise ValueError(f"{label}.reference_offset_in_read_order must be non-zero")
    informative = csv_int(
        row["informative_positions"],
        f"{label}.informative_positions",
        0,
    )
    zero = optional_unit_float(
        row["mean_zero_reference_mass"],
        f"{label}.mean_zero_reference_mass",
    )
    shifted = optional_unit_float(
        row["mean_shifted_reference_mass"],
        f"{label}.mean_shifted_reference_mass",
    )
    residual = optional_unit_float(
        row["mean_residual_mass"],
        f"{label}.mean_residual_mass",
    )

    if informative == 0:
        if any(value is not None for value in (zero, shifted, residual)):
            raise ValueError(
                f"{label}: zero-informative candidate must have empty masses"
            )
    else:
        if zero is None or shifted is None or residual is None:
            raise ValueError(f"{label}: informative candidate requires all masses")
        if abs(zero + shifted + residual - 1.0) > 1e-9:
            raise ValueError(f"{label}: candidate masses must sum to one")

    return CandidateRecord(
        window_id=window_id,
        offset=offset,
        informative_positions=informative,
        zero_mass=zero,
        shifted_mass=shifted,
        residual_mass=residual,
    )


def generated_records(
    window_rows: list[dict[str, Any]],
    hypothesis_rows: list[dict[str, Any]],
) -> tuple[dict[str, WindowRecord], dict[tuple[str, int], CandidateRecord]]:
    windows: dict[str, WindowRecord] = {}
    for index, row in enumerate(window_rows, 2):
        if set(row) != set(WINDOW_COLUMNS):
            raise ValueError(f"generated window row {index - 2} has unexpected columns")
        parsed = parse_window(
            {
                column: "" if row[column] is None else str(row[column])
                for column in WINDOW_COLUMNS
            },
            index,
        )
        if parsed.window_id in windows:
            raise ValueError(f"duplicate generated window_id {parsed.window_id}")
        windows[parsed.window_id] = parsed

    candidates: dict[tuple[str, int], CandidateRecord] = {}
    for index, row in enumerate(hypothesis_rows, 2):
        if set(row) != set(HYPOTHESIS_COLUMNS):
            raise ValueError(
                f"generated hypothesis row {index - 2} has unexpected columns"
            )
        parsed = parse_candidate(
            {
                column: "" if row[column] is None else str(row[column])
                for column in HYPOTHESIS_COLUMNS
            },
            index,
        )
        if parsed.window_id not in windows:
            raise ValueError("generated candidate references unknown window_id")
        key = (parsed.window_id, parsed.offset)
        if key in candidates:
            raise ValueError(f"duplicate generated window/offset candidate {key}")
        candidates[key] = parsed

    return windows, candidates


def load_source(
    source_dir: Path,
    index: dict[str, Any],
    offsets: tuple[int, ...],
) -> tuple[dict[str, WindowRecord], dict[tuple[str, int], CandidateRecord]]:
    windows: dict[str, WindowRecord] = {}
    windows_path = source_dir / "windows.csv"
    with windows_path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or tuple(reader.fieldnames) != WINDOW_COLUMNS:
            raise ValueError(f"{windows_path}: unexpected columns")
        rows_seen = 0
        for line, row in enumerate(reader, 2):
            rows_seen += 1
            parsed = parse_window(row, line)
            if parsed.window_id in windows:
                raise ValueError(
                    f"{windows_path}: duplicate window_id {parsed.window_id}"
                )
            windows[parsed.window_id] = parsed
    if rows_seen != index["windows_rows"]:
        raise ValueError(
            f"{windows_path}: expected {index['windows_rows']} rows, found {rows_seen}"
        )

    candidates: dict[tuple[str, int], CandidateRecord] = {}
    declared_offsets = set(offsets)
    hypotheses_path = source_dir / "hypotheses.csv"
    with hypotheses_path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or tuple(reader.fieldnames) != HYPOTHESIS_COLUMNS:
            raise ValueError(f"{hypotheses_path}: unexpected columns")
        rows_seen = 0
        for line, row in enumerate(reader, 2):
            rows_seen += 1
            parsed = parse_candidate(row, line)
            if parsed.window_id not in windows:
                raise ValueError(
                    f"{hypotheses_path}:{line}: unknown window_id {parsed.window_id}"
                )
            if parsed.offset not in declared_offsets:
                raise ValueError(
                    f"{hypotheses_path}:{line}: offset not declared by source method"
                )
            key = (parsed.window_id, parsed.offset)
            if key in candidates:
                raise ValueError(
                    f"{hypotheses_path}: duplicate window/offset candidate {key}"
                )
            candidates[key] = parsed
    if rows_seen != index["hypotheses_rows"]:
        raise ValueError(
            f"{hypotheses_path}: expected {index['hypotheses_rows']} rows, "
            f"found {rows_seen}"
        )

    for window_id in windows:
        found = {
            offset
            for candidate_window, offset in candidates
            if candidate_window == window_id
        }
        if found != declared_offsets:
            raise ValueError(
                f"{window_id}: candidate curve differs from declared source offsets"
            )
    if len(candidates) != len(windows) * len(offsets):
        raise ValueError("phase-hypothesis candidate curve cardinality is inconsistent")
    return windows, candidates


__all__ = [
    "PRODUCTION_V1_PARAMETERS",
    "CandidateRecord",
    "PhaseHypothesisParameters",
    "WindowRecord",
    "generated_records",
    "load_source",
    "production_v1_parameters",
    "source_offsets",
    "source_parameters",
    "validate_source",
]
