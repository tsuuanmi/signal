"""Parameter-sensitivity summaries for post-poly-C phase hypotheses."""

from __future__ import annotations

import csv
import os
import shutil
import tempfile
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any, TextIO

from .filesystem import file_sha256, sync_directory, validate_new_directory, write_json
from .model import PHASE_SENSITIVITY_SCHEMA_VERSION
from .phase_characterization import aggregate_rows, generated_records
from .phase_hypotheses import (
    load_after_observations,
    nonnegative_int,
    validate_source,
    window_rows,
)

DEFAULT_WINDOW_SIZES = (15, 25, 35)
DEFAULT_WINDOW_STEPS = (5, 10)
DEFAULT_MAX_OFFSETS = (3, 5, 7)

PARAMETER_COLUMNS = (
    "parameter_set_id",
    "window_size_profile_observations",
    "window_step_profile_observations",
    "max_reference_offset_in_read_order",
    "candidate_offsets",
    "windows",
    "hypotheses",
)

STRATA_COLUMNS = (
    "parameter_set_id",
    "window_size_profile_observations",
    "window_step_profile_observations",
    "max_reference_offset_in_read_order",
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


@dataclass(frozen=True, order=True)
class ParameterSet:
    window_size: int
    window_step: int
    max_offset: int

    def __post_init__(self) -> None:
        if self.window_size <= 0 or self.window_step <= 0 or self.max_offset <= 0:
            raise ValueError("phase-sensitivity parameters must be positive")

    @property
    def parameter_set_id(self) -> str:
        return f"w{self.window_size}-s{self.window_step}-o{self.max_offset}"

    @property
    def offsets(self) -> tuple[int, ...]:
        return tuple(range(-self.max_offset, 0)) + tuple(
            range(1, self.max_offset + 1)
        )


def unique_positive(values: tuple[int, ...], label: str) -> tuple[int, ...]:
    if not values:
        raise ValueError(f"{label} must not be empty")
    if any(value <= 0 for value in values):
        raise ValueError(f"{label} values must be positive")
    if len(values) != len(set(values)):
        raise ValueError(f"{label} values must be unique")
    return tuple(sorted(values))


def parameter_grid(
    window_sizes: tuple[int, ...],
    window_steps: tuple[int, ...],
    max_offsets: tuple[int, ...],
) -> tuple[ParameterSet, ...]:
    sizes = unique_positive(window_sizes, "window sizes")
    steps = unique_positive(window_steps, "window steps")
    offsets = unique_positive(max_offsets, "max offsets")
    return tuple(
        ParameterSet(size, step, max_offset)
        for size, step, max_offset in product(sizes, steps, offsets)
    )


def csv_value(value: Any) -> Any:
    return "" if value is None else value


def writer(target: TextIO, columns: tuple[str, ...]) -> csv.DictWriter:
    built = csv.DictWriter(
        target,
        fieldnames=list(columns),
        extrasaction="raise",
        lineterminator="\n",
    )
    built.writeheader()
    return built


def write_row(
    target: csv.DictWriter,
    row: dict[str, Any],
    columns: tuple[str, ...],
    label: str,
) -> None:
    if set(row) != set(columns):
        raise ValueError(f"{label} does not match output columns")
    target.writerow({key: csv_value(row[key]) for key in columns})


def parameter_row(
    parameters: ParameterSet,
    windows: int,
    hypotheses: int,
) -> dict[str, Any]:
    return {
        "parameter_set_id": parameters.parameter_set_id,
        "window_size_profile_observations": parameters.window_size,
        "window_step_profile_observations": parameters.window_step,
        "max_reference_offset_in_read_order": parameters.max_offset,
        "candidate_offsets": ",".join(str(offset) for offset in parameters.offsets),
        "windows": windows,
        "hypotheses": hypotheses,
    }


def prefixed_strata(
    parameters: ParameterSet,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "parameter_set_id": parameters.parameter_set_id,
            "window_size_profile_observations": parameters.window_size,
            "window_step_profile_observations": parameters.window_step,
            "max_reference_offset_in_read_order": parameters.max_offset,
            **row,
        }
        for row in rows
    ]


def output_index(
    phase_dir: Path,
    source_index: dict[str, Any],
    parameter_sets_path: Path,
    strata_path: Path,
    parameters: tuple[ParameterSet, ...],
    parameter_rows: int,
    strata_rows: int,
) -> dict[str, Any]:
    return {
        "schema_version": PHASE_SENSITIVITY_SCHEMA_VERSION,
        "source_polyc_phase_sha256": file_sha256(phase_dir / "index.json"),
        "source_corpus_sha256": source_index["source_corpus_sha256"],
        "signal_version": source_index["signal_version"],
        "manifest_sha256": source_index["manifest_sha256"],
        "reference_sha256": source_index["reference_sha256"],
        "configuration_sha256": source_index["configuration_sha256"],
        "method": {
            "grid": "full factorial",
            "window_sizes_profile_observations": sorted(
                {parameters.window_size for parameters in parameters}
            ),
            "window_steps_profile_observations": sorted(
                {parameters.window_step for parameters in parameters}
            ),
            "max_reference_offsets_in_read_order": sorted(
                {parameters.max_offset for parameters in parameters}
            ),
            "candidate_engine": (
                "same authoritative window/candidate implementation as "
                "signal.validation_phase_hypotheses/v1"
            ),
            "aggregation": (
                "same candidate-wise tract/amplicon/orientation/interrupt strata as "
                "signal.validation_phase_characterization/v1"
            ),
            "candidate_selection": "none; every candidate retained independently",
            "thresholds": "none",
        },
        "parameter_sets_file": "parameter_sets.csv",
        "parameter_sets_sha256": file_sha256(parameter_sets_path),
        "parameter_sets_rows": parameter_rows,
        "parameter_sets_columns": list(PARAMETER_COLUMNS),
        "strata_file": "strata.csv",
        "strata_sha256": file_sha256(strata_path),
        "strata_rows": strata_rows,
        "strata_columns": list(STRATA_COLUMNS),
    }


def build_staged_phase_sensitivity(
    phase_dir: Path,
    source_index: dict[str, Any],
    stage: Path,
    parameters: tuple[ParameterSet, ...],
) -> None:
    groups = load_after_observations(
        phase_dir,
        nonnegative_int(source_index["observations_rows"], "observations_rows"),
    )
    if not groups:
        raise ValueError("poly-C phase artifact contains no post-tract observations")

    parameter_sets_path = stage / "parameter_sets.csv"
    strata_path = stage / "strata.csv"
    parameter_count = 0
    strata_count = 0

    with (
        parameter_sets_path.open("x", encoding="utf-8", newline="") as parameters_file,
        strata_path.open("x", encoding="utf-8", newline="") as strata_file,
    ):
        parameters_writer = writer(parameters_file, PARAMETER_COLUMNS)
        strata_writer = writer(strata_file, STRATA_COLUMNS)

        for parameter_set in parameters:
            windows_rows, hypothesis_rows = window_rows(
                groups,
                parameter_set.window_size,
                parameter_set.window_step,
                parameter_set.max_offset,
            )
            windows, candidates = generated_records(windows_rows, hypothesis_rows)
            strata = aggregate_rows(
                windows,
                candidates,
                parameter_set.offsets,
                trajectory=False,
            )

            write_row(
                parameters_writer,
                parameter_row(
                    parameter_set,
                    len(windows_rows),
                    len(hypothesis_rows),
                ),
                PARAMETER_COLUMNS,
                f"parameter set {parameter_count}",
            )
            parameter_count += 1

            for row in prefixed_strata(parameter_set, strata):
                write_row(
                    strata_writer,
                    row,
                    STRATA_COLUMNS,
                    f"sensitivity stratum {strata_count}",
                )
                strata_count += 1

        parameters_file.flush()
        os.fsync(parameters_file.fileno())
        strata_file.flush()
        os.fsync(strata_file.fileno())

    write_json(
        stage / "index.json",
        output_index(
            phase_dir,
            source_index,
            parameter_sets_path,
            strata_path,
            parameters,
            parameter_count,
            strata_count,
        ),
    )
    sync_directory(stage)


def publish_phase_sensitivity(
    phase_dir: Path,
    output_dir: Path,
    *,
    window_sizes: tuple[int, ...] = DEFAULT_WINDOW_SIZES,
    window_steps: tuple[int, ...] = DEFAULT_WINDOW_STEPS,
    max_offsets: tuple[int, ...] = DEFAULT_MAX_OFFSETS,
) -> None:
    phase_dir = phase_dir.resolve()
    output_dir = output_dir.resolve()
    if not phase_dir.is_dir():
        raise ValueError(f"poly-C phase directory does not exist: {phase_dir}")
    validate_new_directory(output_dir, (phase_dir,))
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if not output_dir.parent.is_dir() or output_dir.parent.is_symlink():
        raise ValueError(
            f"output parent is not a regular directory: {output_dir.parent}"
        )

    source_index = validate_source(phase_dir)
    parameters = parameter_grid(window_sizes, window_steps, max_offsets)
    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        build_staged_phase_sensitivity(
            phase_dir,
            source_index,
            stage,
            parameters,
        )
        try:
            output_dir.mkdir()
        except FileExistsError as error:
            raise FileExistsError(
                "output directory appeared while phase sensitivity was running: "
                f"{output_dir}"
            ) from error
        try:
            for name in ("parameter_sets.csv", "strata.csv", "index.json"):
                os.rename(stage / name, output_dir / name)
            sync_directory(output_dir)
            sync_directory(output_dir.parent)
        except OSError:
            shutil.rmtree(output_dir, ignore_errors=True)
            sync_directory(output_dir.parent)
            raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
