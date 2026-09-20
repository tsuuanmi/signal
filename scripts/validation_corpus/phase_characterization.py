"""Descriptive characterization of post-poly-C phase-hypothesis curves."""

from __future__ import annotations

import csv
import os
import shutil
import tempfile
from itertools import pairwise
from pathlib import Path
from typing import Any, TextIO

from .filesystem import file_sha256, sync_directory, validate_new_directory, write_json
from .model import PHASE_CHARACTERIZATION_SCHEMA_VERSION
from .phase_artifact import (
    CandidateRecord,
    load_source,
    validate_source,
    WindowRecord,
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
