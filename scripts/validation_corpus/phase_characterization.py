"""Descriptive characterization of post-poly-C phase-hypothesis curves."""

from __future__ import annotations

import csv
import math
import os
import shutil
import tempfile
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any, TextIO

from .filesystem import file_sha256, sync_directory, validate_new_directory, write_json
from .model import (
    PHASE_CHARACTERIZATION_SCHEMA_VERSION,
    PHASE_HYPOTHESIS_SCHEMA_VERSION,
)
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

PERSISTENCE_COLUMNS = (
    "validation_case_id",
    "read_sha256",
    "tract_id",
    "amplicon_id",
    "orientation",
    "interrupt_aligned_base",
    "reference_offset_in_read_order",
    "left_window_id",
    "right_window_id",
    "left_start_distance_after_tract",
    "right_start_distance_after_tract",
    "left_informative_positions",
    "right_informative_positions",
    "left_mean_zero_reference_mass",
    "right_mean_zero_reference_mass",
    "left_mean_shifted_reference_mass",
    "right_mean_shifted_reference_mass",
    "left_mean_residual_mass",
    "right_mean_residual_mass",
    "absolute_zero_reference_mass_delta",
    "absolute_shifted_reference_mass_delta",
    "absolute_residual_mass_delta",
)

TRAJECTORY_COLUMNS = (
    "tract_id",
    "amplicon_id",
    "orientation",
    "interrupt_aligned_base",
    "start_distance_after_tract",
    "reference_offset_in_read_order",
    "windows",
    "informative_windows",
    "mean_informative_positions",
    "mean_zero_reference_mass",
    "mean_shifted_reference_mass",
    "mean_residual_mass",
    "mean_window_profile_impurity",
    "mean_window_noisy_fraction",
)

STRATA_COLUMNS = (
    "tract_id",
    "amplicon_id",
    "orientation",
    "interrupt_aligned_base",
    "reference_offset_in_read_order",
    "windows",
    "informative_windows",
    "mean_informative_positions",
    "mean_zero_reference_mass",
    "mean_shifted_reference_mass",
    "mean_residual_mass",
    "mean_window_profile_impurity",
    "mean_window_noisy_fraction",
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
    profile_observations: int
    noisy_observations: int
    mean_profile_impurity: float


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
    return index, source_offsets(index["method"])


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
        profile_observations=profile_count,
        noisy_observations=noisy_count,
        mean_profile_impurity=unit_float(
            row["mean_profile_impurity"],
            f"{label}.mean_profile_impurity",
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
            raise ValueError(f"generated candidate references unknown window_id")
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


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def mean_or_none(values: list[float]) -> float | None:
    return mean(values) if values else None


def candidate_summary(
    rows: list[tuple[WindowRecord, CandidateRecord]],
) -> dict[str, Any]:
    informative = [
        candidate for _, candidate in rows if candidate.informative_positions
    ]
    return {
        "windows": len(rows),
        "informative_windows": len(informative),
        "mean_informative_positions": mean(
            [float(candidate.informative_positions) for _, candidate in rows]
        ),
        "mean_zero_reference_mass": mean_or_none(
            [
                candidate.zero_mass
                for candidate in informative
                if candidate.zero_mass is not None
            ]
        ),
        "mean_shifted_reference_mass": mean_or_none(
            [
                candidate.shifted_mass
                for candidate in informative
                if candidate.shifted_mass is not None
            ]
        ),
        "mean_residual_mass": mean_or_none(
            [
                candidate.residual_mass
                for candidate in informative
                if candidate.residual_mass is not None
            ]
        ),
        "mean_window_profile_impurity": mean(
            [window.mean_profile_impurity for window, _ in rows]
        ),
        "mean_window_noisy_fraction": mean(
            [
                window.noisy_observations / window.profile_observations
                for window, _ in rows
            ]
        ),
    }


def absolute_delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return abs(right - left)


def persistence_rows(
    windows: dict[str, WindowRecord],
    candidates: dict[tuple[str, int], CandidateRecord],
    offsets: tuple[int, ...],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[WindowRecord]] = {}
    for window in windows.values():
        grouped.setdefault((window.read_sha256, window.tract_id), []).append(window)

    output: list[dict[str, Any]] = []
    for key in sorted(grouped):
        ordered = sorted(grouped[key], key=lambda window: window.start_distance)
        starts = [window.start_distance for window in ordered]
        if len(starts) != len(set(starts)):
            raise ValueError(f"{key}: duplicate window start distance")
        first = ordered[0]
        for window in ordered[1:]:
            if (
                window.validation_case_id != first.validation_case_id
                or window.amplicon_id != first.amplicon_id
                or window.orientation != first.orientation
                or window.interrupt_aligned_base != first.interrupt_aligned_base
            ):
                raise ValueError(
                    f"{key}: window metadata changes across one read/tract"
                )

        for left, right in pairwise(ordered):
            for offset in offsets:
                left_candidate = candidates[(left.window_id, offset)]
                right_candidate = candidates[(right.window_id, offset)]
                output.append(
                    {
                        "validation_case_id": left.validation_case_id,
                        "read_sha256": left.read_sha256,
                        "tract_id": left.tract_id,
                        "amplicon_id": left.amplicon_id,
                        "orientation": left.orientation,
                        "interrupt_aligned_base": left.interrupt_aligned_base,
                        "reference_offset_in_read_order": offset,
                        "left_window_id": left.window_id,
                        "right_window_id": right.window_id,
                        "left_start_distance_after_tract": left.start_distance,
                        "right_start_distance_after_tract": right.start_distance,
                        "left_informative_positions": (
                            left_candidate.informative_positions
                        ),
                        "right_informative_positions": (
                            right_candidate.informative_positions
                        ),
                        "left_mean_zero_reference_mass": left_candidate.zero_mass,
                        "right_mean_zero_reference_mass": right_candidate.zero_mass,
                        "left_mean_shifted_reference_mass": (
                            left_candidate.shifted_mass
                        ),
                        "right_mean_shifted_reference_mass": (
                            right_candidate.shifted_mass
                        ),
                        "left_mean_residual_mass": left_candidate.residual_mass,
                        "right_mean_residual_mass": right_candidate.residual_mass,
                        "absolute_zero_reference_mass_delta": absolute_delta(
                            left_candidate.zero_mass,
                            right_candidate.zero_mass,
                        ),
                        "absolute_shifted_reference_mass_delta": absolute_delta(
                            left_candidate.shifted_mass,
                            right_candidate.shifted_mass,
                        ),
                        "absolute_residual_mass_delta": absolute_delta(
                            left_candidate.residual_mass,
                            right_candidate.residual_mass,
                        ),
                    }
                )
    return output


def aggregate_rows(
    windows: dict[str, WindowRecord],
    candidates: dict[tuple[str, int], CandidateRecord],
    offsets: tuple[int, ...],
    *,
    trajectory: bool,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[tuple[WindowRecord, CandidateRecord]]] = {}
    for window in windows.values():
        for offset in offsets:
            candidate = candidates[(window.window_id, offset)]
            base: tuple[Any, ...] = (
                window.tract_id,
                window.amplicon_id,
                window.orientation,
                window.interrupt_aligned_base,
            )
            key = (
                (*base, window.start_distance, offset)
                if trajectory
                else (*base, offset)
            )
            grouped.setdefault(key, []).append((window, candidate))

    output: list[dict[str, Any]] = []
    for key in sorted(grouped):
        rows = grouped[key]
        tract_id, amplicon_id, orientation, interrupt = key[:4]
        built: dict[str, Any] = {
            "tract_id": tract_id,
            "amplicon_id": amplicon_id,
            "orientation": orientation,
            "interrupt_aligned_base": interrupt,
            "reference_offset_in_read_order": key[-1],
            **candidate_summary(rows),
        }
        if trajectory:
            built["start_distance_after_tract"] = key[4]
        output.append(built)
    return output


def csv_value(value: Any) -> Any:
    return "" if value is None else value


def csv_writer(target: TextIO, columns: tuple[str, ...]) -> csv.DictWriter:
    built = csv.DictWriter(
        target,
        fieldnames=list(columns),
        extrasaction="raise",
        lineterminator="\n",
    )
    built.writeheader()
    return built


def write_rows(
    path: Path,
    rows: list[dict[str, Any]],
    columns: tuple[str, ...],
    label: str,
) -> None:
    with path.open("x", encoding="utf-8", newline="") as target:
        writer = csv_writer(target, columns)
        for index, row in enumerate(rows):
            if set(row) != set(columns):
                raise ValueError(f"{label} row {index} does not match output columns")
            writer.writerow({key: csv_value(row[key]) for key in columns})
        target.flush()
        os.fsync(target.fileno())


def output_index(
    source_dir: Path,
    source_index: dict[str, Any],
    offsets: tuple[int, ...],
    persistence_path: Path,
    trajectory_path: Path,
    strata_path: Path,
    persistence: list[dict[str, Any]],
    trajectory: list[dict[str, Any]],
    strata: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": PHASE_CHARACTERIZATION_SCHEMA_VERSION,
        "source_phase_hypotheses_sha256": file_sha256(source_dir / "index.json"),
        "source_polyc_phase_sha256": source_index["source_polyc_phase_sha256"],
        "source_corpus_sha256": source_index["source_corpus_sha256"],
        "signal_version": source_index["signal_version"],
        "manifest_sha256": source_index["manifest_sha256"],
        "reference_sha256": source_index["reference_sha256"],
        "configuration_sha256": source_index["configuration_sha256"],
        "method": {
            "candidate_offsets": list(offsets),
            "adjacency": (
                "consecutive source windows for one read/tract, compared at the same "
                "candidate offset"
            ),
            "trajectory_distance": (
                "exact source window start distance after tract in read order; no bins"
            ),
            "interrupt_stratification": (
                "observed read-local interrupt base; no genotype interpretation"
            ),
            "candidate_selection": (
                "none; every source candidate retained independently"
            ),
            "thresholds": "none",
        },
        "persistence_file": "persistence.csv",
        "persistence_sha256": file_sha256(persistence_path),
        "persistence_rows": len(persistence),
        "persistence_columns": list(PERSISTENCE_COLUMNS),
        "trajectory_file": "trajectory.csv",
        "trajectory_sha256": file_sha256(trajectory_path),
        "trajectory_rows": len(trajectory),
        "trajectory_columns": list(TRAJECTORY_COLUMNS),
        "strata_file": "strata.csv",
        "strata_sha256": file_sha256(strata_path),
        "strata_rows": len(strata),
        "strata_columns": list(STRATA_COLUMNS),
    }


def publish_phase_characterization(source_dir: Path, output_dir: Path) -> None:
    source_dir = source_dir.resolve()
    output_dir = output_dir.resolve()
    if not source_dir.is_dir():
        raise ValueError(f"phase-hypothesis directory does not exist: {source_dir}")
    validate_new_directory(output_dir, (source_dir,))
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if not output_dir.parent.is_dir() or output_dir.parent.is_symlink():
        raise ValueError(
            f"output parent is not a regular directory: {output_dir.parent}"
        )

    source_index, offsets = validate_source(source_dir)
    windows, candidates = load_source(source_dir, source_index, offsets)
    if not windows:
        raise ValueError("phase-hypothesis artifact contains no windows")
    persistence = persistence_rows(windows, candidates, offsets)
    trajectory = aggregate_rows(windows, candidates, offsets, trajectory=True)
    strata = aggregate_rows(windows, candidates, offsets, trajectory=False)

    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        persistence_path = stage / "persistence.csv"
        trajectory_path = stage / "trajectory.csv"
        strata_path = stage / "strata.csv"
        write_rows(persistence_path, persistence, PERSISTENCE_COLUMNS, "persistence")
        write_rows(trajectory_path, trajectory, TRAJECTORY_COLUMNS, "trajectory")
        write_rows(strata_path, strata, STRATA_COLUMNS, "strata")
        write_json(
            stage / "index.json",
            output_index(
                source_dir,
                source_index,
                offsets,
                persistence_path,
                trajectory_path,
                strata_path,
                persistence,
                trajectory,
                strata,
            ),
        )
        sync_directory(stage)

        try:
            output_dir.mkdir()
        except FileExistsError as error:
            raise FileExistsError(
                f"output directory appeared while phase characterization was running: "
                f"{output_dir}"
            ) from error
        try:
            for name in (
                "persistence.csv",
                "trajectory.csv",
                "strata.csv",
                "index.json",
            ):
                os.rename(stage / name, output_dir / name)
            sync_directory(output_dir)
            sync_directory(output_dir.parent)
        except OSError:
            shutil.rmtree(output_dir, ignore_errors=True)
            sync_directory(output_dir.parent)
            raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
