"""Direct parity checks between Rust runtime phase evidence and Python research evidence."""

from __future__ import annotations

import csv
import math
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .filesystem import file_sha256
from .phase_artifact import (
    CandidateRecord,
    WindowRecord,
    load_source,
    source_parameters,
    validate_source,
)
from .research_loader import json_object, strict_keys

RUNTIME_SCHEMA_VERSION = "signal.validation_phase_runtime/v1"
RUNTIME_SOURCE_METHOD = "signal.polyc_phase/v1"

RUNTIME_INDEX_FIELDS = (
    "schema_version",
    "source_method",
    "signal_version",
    "sample_id",
    "reference_sha256",
    "configuration_sha256",
    "read_count",
    "window_count",
    "candidate_count",
    "files",
    "reads",
)
RUNTIME_FILE_FIELDS = ("path", "sha256", "rows")

RUNTIME_WINDOW_COLUMNS = (
    "read_sha256",
    "tract_id",
    "start_distance_after_tract",
    "end_distance_after_tract",
    "start_call_index_0based",
    "end_call_index_0based",
    "profile_observations",
    "mean_profile_impurity",
    "mean_zero_reference_mass",
)
RUNTIME_CANDIDATE_COLUMNS = (
    "read_sha256",
    "tract_id",
    "start_distance_after_tract",
    "end_distance_after_tract",
    "reference_offset_in_read_order",
    "informative_positions",
    "mean_zero_reference_mass",
    "mean_shifted_reference_mass",
    "mean_residual_mass",
)

WindowKey = tuple[str, str, int, int]
CandidateKey = tuple[str, str, int, int, int]


@dataclass(frozen=True)
class RuntimeWindow:
    key: WindowKey
    start_call_index: int
    end_call_index: int
    profile_observations: int
    mean_profile_impurity: float
    mean_zero_reference_mass: float


@dataclass(frozen=True)
class RuntimeCandidate:
    key: CandidateKey
    informative_positions: int
    zero_mass: float | None
    shifted_mass: float | None
    residual_mass: float | None


@dataclass(frozen=True)
class ParitySummary:
    research_windows: int
    runtime_windows: int
    missing_windows: int
    extra_windows: int
    call_index_diffs: int
    profile_observation_diffs: int
    research_candidates: int
    runtime_candidates: int
    missing_candidates: int
    extra_candidates: int
    candidate_count_diff: int
    informative_count_diff: int
    numeric_presence_diff: int
    max_numeric_delta: float
    tolerance: float

    @property
    def passed(self) -> bool:
        return (
            self.missing_windows == 0
            and self.extra_windows == 0
            and self.call_index_diffs == 0
            and self.profile_observation_diffs == 0
            and self.missing_candidates == 0
            and self.extra_candidates == 0
            and self.candidate_count_diff == 0
            and self.informative_count_diff == 0
            and self.numeric_presence_diff == 0
            and self.max_numeric_delta <= self.tolerance
        )


def nonnegative_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def csv_int(value: str, label: str, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{label} must be an integer") from error
    if parsed < minimum:
        raise ValueError(f"{label} must be >= {minimum}")
    return parsed


def csv_unit_float(value: str, label: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise ValueError(f"{label} must be numeric") from error
    if not math.isfinite(parsed) or not 0.0 <= parsed <= 1.0:
        raise ValueError(f"{label} must be finite in [0, 1]")
    return parsed


def optional_unit_float(value: str, label: str) -> float | None:
    return None if value == "" else csv_unit_float(value, label)


def window_key(
    read_sha256: str,
    tract_id: str,
    start_distance: int,
    end_distance: int,
) -> WindowKey:
    return read_sha256, tract_id, start_distance, end_distance


def research_window_key(window: WindowRecord) -> WindowKey:
    return window_key(
        window.read_sha256,
        window.tract_id,
        window.start_distance,
        window.end_distance,
    )


def research_candidate_key(
    window: WindowRecord,
    candidate: CandidateRecord,
) -> CandidateKey:
    return (*research_window_key(window), candidate.offset)


def validate_runtime_index(runtime_dir: Path) -> dict[str, Any]:
    index_path = runtime_dir / "index.json"
    if not index_path.is_file():
        raise ValueError(f"runtime phase index is not a regular file: {index_path}")
    index = json_object(index_path)
    strict_keys(index, RUNTIME_INDEX_FIELDS, "runtime phase index")
    if index["schema_version"] != RUNTIME_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported runtime phase schema: {index['schema_version']!r}"
        )
    if index["source_method"] != RUNTIME_SOURCE_METHOD:
        raise ValueError(
            f"unsupported runtime phase source method: {index['source_method']!r}"
        )
    if not isinstance(index["sample_id"], str) or not index["sample_id"]:
        raise ValueError("runtime phase sample_id must be a non-empty string")

    files = index["files"]
    if not isinstance(files, dict):
        raise TypeError("runtime phase files must be an object")
    strict_keys(files, ("windows", "candidates"), "runtime phase files")

    specs = (
        ("windows", "windows.csv", index["window_count"]),
        ("candidates", "candidates.csv", index["candidate_count"]),
    )
    for key, filename, declared_count in specs:
        entry = files[key]
        if not isinstance(entry, dict):
            raise TypeError(f"runtime phase files.{key} must be an object")
        strict_keys(entry, RUNTIME_FILE_FIELDS, f"runtime phase files.{key}")
        if entry["path"] != filename:
            raise ValueError(f"runtime phase files.{key}.path must be {filename}")
        rows = nonnegative_int(entry["rows"], f"runtime phase files.{key}.rows")
        count = nonnegative_int(declared_count, f"runtime phase {key[:-1]}_count")
        if rows != count:
            raise ValueError(f"runtime phase {key} row count differs from index count")
        path = runtime_dir / filename
        if not path.is_file():
            raise ValueError(f"runtime phase table is not a regular file: {path}")
        if entry["sha256"] != file_sha256(path):
            raise ValueError(f"{filename} SHA-256 mismatch")

    nonnegative_int(index["read_count"], "runtime phase read_count")
    reads = index["reads"]
    if not isinstance(reads, list) or len(reads) != index["read_count"]:
        raise ValueError("runtime phase reads differ from read_count")
    return index


def load_runtime(
    runtime_dirs: Iterable[Path],
    *,
    signal_version: str,
    reference_sha256: str,
    configuration_sha256: str,
) -> tuple[dict[WindowKey, RuntimeWindow], dict[CandidateKey, RuntimeCandidate]]:
    windows: dict[WindowKey, RuntimeWindow] = {}
    candidates: dict[CandidateKey, RuntimeCandidate] = {}
    sample_ids: set[str] = set()

    for runtime_dir in sorted((path.resolve() for path in runtime_dirs), key=str):
        index = validate_runtime_index(runtime_dir)
        if index["signal_version"] != signal_version:
            raise ValueError(
                f"{runtime_dir}: Signal version differs from research artifact"
            )
        if index["reference_sha256"] != reference_sha256:
            raise ValueError(
                f"{runtime_dir}: reference SHA-256 differs from research artifact"
            )
        if index["configuration_sha256"] != configuration_sha256:
            raise ValueError(
                f"{runtime_dir}: configuration SHA-256 differs from research artifact"
            )
        sample_id = index["sample_id"]
        if sample_id in sample_ids:
            raise ValueError(f"duplicate runtime phase sample_id {sample_id}")
        sample_ids.add(sample_id)

        window_path = runtime_dir / "windows.csv"
        with window_path.open("r", encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            if (
                reader.fieldnames is None
                or tuple(reader.fieldnames) != RUNTIME_WINDOW_COLUMNS
            ):
                raise ValueError(f"{window_path}: unexpected columns")
            rows = 0
            for line, row in enumerate(reader, 2):
                rows += 1
                label = f"{window_path}:{line}"
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
                key = window_key(row["read_sha256"], row["tract_id"], start, end)
                if not key[0] or not key[1]:
                    raise ValueError(f"{label}: missing read/tract identity")
                if key in windows:
                    raise ValueError(f"duplicate runtime phase window {key}")
                start_call = csv_int(
                    row["start_call_index_0based"],
                    f"{label}.start_call_index_0based",
                )
                end_call = csv_int(
                    row["end_call_index_0based"],
                    f"{label}.end_call_index_0based",
                )
                if end_call < start_call:
                    raise ValueError(f"{label}: call-index end precedes start")
                windows[key] = RuntimeWindow(
                    key=key,
                    start_call_index=start_call,
                    end_call_index=end_call,
                    profile_observations=csv_int(
                        row["profile_observations"],
                        f"{label}.profile_observations",
                        1,
                    ),
                    mean_profile_impurity=csv_unit_float(
                        row["mean_profile_impurity"],
                        f"{label}.mean_profile_impurity",
                    ),
                    mean_zero_reference_mass=csv_unit_float(
                        row["mean_zero_reference_mass"],
                        f"{label}.mean_zero_reference_mass",
                    ),
                )
        if rows != index["window_count"]:
            raise ValueError(f"{window_path}: row count differs from index")

        candidate_path = runtime_dir / "candidates.csv"
        with candidate_path.open("r", encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            if (
                reader.fieldnames is None
                or tuple(reader.fieldnames) != RUNTIME_CANDIDATE_COLUMNS
            ):
                raise ValueError(f"{candidate_path}: unexpected columns")
            rows = 0
            for line, row in enumerate(reader, 2):
                rows += 1
                label = f"{candidate_path}:{line}"
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
                offset = csv_int(
                    row["reference_offset_in_read_order"],
                    f"{label}.reference_offset_in_read_order",
                    -128,
                )
                if offset == 0:
                    raise ValueError(
                        f"{label}.reference_offset_in_read_order must be non-zero"
                    )
                key = (
                    row["read_sha256"],
                    row["tract_id"],
                    start,
                    end,
                    offset,
                )
                if key[:-1] not in windows:
                    raise ValueError(
                        f"{label}: candidate references unknown runtime window"
                    )
                if key in candidates:
                    raise ValueError(f"duplicate runtime phase candidate {key}")
                informative = csv_int(
                    row["informative_positions"],
                    f"{label}.informative_positions",
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
                elif zero is None or shifted is None or residual is None:
                    raise ValueError(
                        f"{label}: informative candidate requires all masses"
                    )
                candidates[key] = RuntimeCandidate(
                    key=key,
                    informative_positions=informative,
                    zero_mass=zero,
                    shifted_mass=shifted,
                    residual_mass=residual,
                )
        if rows != index["candidate_count"]:
            raise ValueError(f"{candidate_path}: row count differs from index")

    return windows, candidates


def numeric_delta(left: float | None, right: float | None) -> tuple[int, float]:
    if left is None or right is None:
        return (0, 0.0) if left is right else (1, 0.0)
    return 0, abs(left - right)


def compare_phase_runtime(
    research_dir: Path,
    runtime_dirs: Iterable[Path],
    *,
    tolerance: float = 1e-12,
) -> ParitySummary:
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("numeric tolerance must be finite and non-negative")

    research_index, offsets = validate_source(research_dir)
    parameters = source_parameters(research_index["method"])
    if (
        parameters.window_size != 25
        or parameters.window_step != 5
        or parameters.max_offset != 5
    ):
        raise ValueError(
            "research phase method does not match signal.polyc_phase/v1 constants"
        )
    research_windows_by_id, research_candidates_by_id = load_source(
        research_dir,
        research_index,
        offsets,
    )
    runtime_windows, runtime_candidates = load_runtime(
        runtime_dirs,
        signal_version=research_index["signal_version"],
        reference_sha256=research_index["reference_sha256"],
        configuration_sha256=research_index["configuration_sha256"],
    )

    research_windows: dict[WindowKey, WindowRecord] = {}
    for window in research_windows_by_id.values():
        key = research_window_key(window)
        if key in research_windows:
            raise ValueError(f"duplicate research phase window identity {key}")
        research_windows[key] = window

    research_candidates: dict[CandidateKey, CandidateRecord] = {}
    for (window_id, _), candidate in research_candidates_by_id.items():
        window = research_windows_by_id[window_id]
        key = research_candidate_key(window, candidate)
        if key in research_candidates:
            raise ValueError(f"duplicate research phase candidate identity {key}")
        research_candidates[key] = candidate

    research_window_keys = set(research_windows)
    runtime_window_keys = set(runtime_windows)
    common_windows = research_window_keys & runtime_window_keys

    call_index_diffs = 0
    profile_observation_diffs = 0
    numeric_presence_diff = 0
    max_numeric_delta = 0.0

    for key in common_windows:
        research = research_windows[key]
        runtime = runtime_windows[key]
        if (
            research.start_call_index != runtime.start_call_index
            or research.end_call_index != runtime.end_call_index
        ):
            call_index_diffs += 1
        if research.profile_observations != runtime.profile_observations:
            profile_observation_diffs += 1
        max_numeric_delta = max(
            max_numeric_delta,
            abs(research.mean_profile_impurity - runtime.mean_profile_impurity),
            abs(research.mean_zero_reference_mass - runtime.mean_zero_reference_mass),
        )

    research_candidate_keys = set(research_candidates)
    runtime_candidate_keys = set(runtime_candidates)
    common_candidates = research_candidate_keys & runtime_candidate_keys
    informative_count_diff = 0

    for key in common_candidates:
        research = research_candidates[key]
        runtime = runtime_candidates[key]
        if research.informative_positions != runtime.informative_positions:
            informative_count_diff += 1
        for left, right in (
            (research.zero_mass, runtime.zero_mass),
            (research.shifted_mass, runtime.shifted_mass),
            (research.residual_mass, runtime.residual_mass),
        ):
            presence_diff, delta = numeric_delta(left, right)
            numeric_presence_diff += presence_diff
            max_numeric_delta = max(max_numeric_delta, delta)

    return ParitySummary(
        research_windows=len(research_windows),
        runtime_windows=len(runtime_windows),
        missing_windows=len(research_window_keys - runtime_window_keys),
        extra_windows=len(runtime_window_keys - research_window_keys),
        call_index_diffs=call_index_diffs,
        profile_observation_diffs=profile_observation_diffs,
        research_candidates=len(research_candidates),
        runtime_candidates=len(runtime_candidates),
        missing_candidates=len(research_candidate_keys - runtime_candidate_keys),
        extra_candidates=len(runtime_candidate_keys - research_candidate_keys),
        candidate_count_diff=abs(len(research_candidates) - len(runtime_candidates)),
        informative_count_diff=informative_count_diff,
        numeric_presence_diff=numeric_presence_diff,
        max_numeric_delta=max_numeric_delta,
        tolerance=tolerance,
    )


__all__ = [
    "ParitySummary",
    "compare_phase_runtime",
]
