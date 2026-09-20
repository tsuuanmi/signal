"""Threshold-free candidate explainability summaries for post-poly-C windows."""

from __future__ import annotations

import csv
import math
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from .filesystem import file_sha256, sync_directory, validate_new_directory, write_json
from .model import PHASE_EXPLAINABILITY_SCHEMA_VERSION
from .phase_artifact import (
    CandidateRecord,
    WindowRecord,
    load_source,
    validate_source,
)

WINDOW_COLUMNS = (
    "window_id",
    "validation_case_id",
    "read_sha256",
    "tract_id",
    "amplicon_id",
    "orientation",
    "interrupt_aligned_base",
    "start_distance_after_tract",
    "end_distance_after_tract",
    "profile_observations",
    "noisy_observations",
    "noisy_fraction",
    "mean_profile_impurity",
    "mean_zero_reference_mass",
    "candidate_count",
    "informative_candidates",
    "explainability_candidates",
    "max_informative_positions",
    "mean_informative_positions",
    "candidate_shifted_reference_mass_min",
    "candidate_shifted_reference_mass_max",
    "candidate_shifted_reference_mass_range",
    "candidate_residual_mass_min",
    "candidate_residual_mass_max",
    "candidate_residual_mass_range",
    "candidate_explainable_nonzero_fraction_max",
)

READ_COLUMNS = (
    "validation_case_id",
    "read_sha256",
    "tract_id",
    "amplicon_id",
    "orientation",
    "interrupt_aligned_base",
    "windows",
    "windows_without_informative_candidates",
    "windows_without_explainability_candidates",
    "mean_window_profile_impurity",
    "max_window_profile_impurity",
    "mean_window_noisy_fraction",
    "mean_candidate_shifted_reference_mass_max",
    "max_candidate_shifted_reference_mass_max",
    "mean_candidate_residual_mass_min",
    "max_candidate_residual_mass_min",
    "mean_candidate_explainable_nonzero_fraction_max",
    "min_candidate_explainable_nonzero_fraction_max",
    "mean_candidate_shifted_reference_mass_range",
    "mean_candidate_residual_mass_range",
)


@dataclass(frozen=True)
class WindowExplainability:
    window: WindowRecord
    candidate_count: int
    informative_candidates: int
    explainability_candidates: int
    max_informative_positions: int
    mean_informative_positions: float | None
    shifted_min: float | None
    shifted_max: float | None
    residual_min: float | None
    residual_max: float | None
    explainable_nonzero_fraction_max: float | None

    @property
    def shifted_range(self) -> float | None:
        if self.shifted_min is None or self.shifted_max is None:
            return None
        return self.shifted_max - self.shifted_min

    @property
    def residual_range(self) -> float | None:
        if self.residual_min is None or self.residual_max is None:
            return None
        return self.residual_max - self.residual_min


def mean(values: list[float]) -> float:
    return math.fsum(values) / len(values)


def mean_or_none(values: list[float]) -> float | None:
    return mean(values) if values else None


def min_or_none(values: list[float]) -> float | None:
    return min(values) if values else None


def max_or_none(values: list[float]) -> float | None:
    return max(values) if values else None


def envelope(
    window: WindowRecord,
    candidates: list[CandidateRecord],
) -> WindowExplainability:
    informative = [
        candidate for candidate in candidates if candidate.informative_positions > 0
    ]
    shifted = [
        candidate.shifted_mass
        for candidate in informative
        if candidate.shifted_mass is not None
    ]
    residual = [
        candidate.residual_mass
        for candidate in informative
        if candidate.residual_mass is not None
    ]
    if len(shifted) != len(informative) or len(residual) != len(informative):
        raise ValueError(f"{window.window_id}: informative candidate mass is missing")

    explainable_fractions: list[float] = []
    for candidate in informative:
        if candidate.shifted_mass is None or candidate.residual_mass is None:
            raise ValueError(
                f"{window.window_id}: informative candidate mass is missing"
            )
        nonzero = candidate.shifted_mass + candidate.residual_mass
        if nonzero > 0.0:
            explainable_fractions.append(candidate.shifted_mass / nonzero)

    informative_positions = [
        float(candidate.informative_positions) for candidate in informative
    ]
    return WindowExplainability(
        window=window,
        candidate_count=len(candidates),
        informative_candidates=len(informative),
        explainability_candidates=len(explainable_fractions),
        max_informative_positions=max(
            (candidate.informative_positions for candidate in informative),
            default=0,
        ),
        mean_informative_positions=mean_or_none(informative_positions),
        shifted_min=min_or_none(shifted),
        shifted_max=max_or_none(shifted),
        residual_min=min_or_none(residual),
        residual_max=max_or_none(residual),
        explainable_nonzero_fraction_max=max_or_none(explainable_fractions),
    )


def build_envelopes(
    windows: dict[str, WindowRecord],
    candidates: dict[tuple[str, int], CandidateRecord],
    offsets: tuple[int, ...],
) -> list[WindowExplainability]:
    output: list[WindowExplainability] = []
    for window in sorted(
        windows.values(),
        key=lambda value: (
            value.validation_case_id,
            value.read_sha256,
            value.tract_id,
            value.start_distance,
            value.window_id,
        ),
    ):
        curve = [candidates[(window.window_id, offset)] for offset in offsets]
        output.append(envelope(window, curve))
    return output


def window_row(item: WindowExplainability) -> dict[str, Any]:
    window = item.window
    return {
        "window_id": window.window_id,
        "validation_case_id": window.validation_case_id,
        "read_sha256": window.read_sha256,
        "tract_id": window.tract_id,
        "amplicon_id": window.amplicon_id,
        "orientation": window.orientation,
        "interrupt_aligned_base": window.interrupt_aligned_base,
        "start_distance_after_tract": window.start_distance,
        "end_distance_after_tract": window.end_distance,
        "profile_observations": window.profile_observations,
        "noisy_observations": window.noisy_observations,
        "noisy_fraction": window.noisy_observations / window.profile_observations,
        "mean_profile_impurity": window.mean_profile_impurity,
        "mean_zero_reference_mass": window.mean_zero_reference_mass,
        "candidate_count": item.candidate_count,
        "informative_candidates": item.informative_candidates,
        "explainability_candidates": item.explainability_candidates,
        "max_informative_positions": item.max_informative_positions,
        "mean_informative_positions": item.mean_informative_positions,
        "candidate_shifted_reference_mass_min": item.shifted_min,
        "candidate_shifted_reference_mass_max": item.shifted_max,
        "candidate_shifted_reference_mass_range": item.shifted_range,
        "candidate_residual_mass_min": item.residual_min,
        "candidate_residual_mass_max": item.residual_max,
        "candidate_residual_mass_range": item.residual_range,
        "candidate_explainable_nonzero_fraction_max": (
            item.explainable_nonzero_fraction_max
        ),
    }


def optional_values(
    rows: list[dict[str, Any]],
    key: str,
) -> list[float]:
    return [float(row[key]) for row in rows if row[key] is not None]


def read_rows(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in windows:
        grouped.setdefault((str(row["read_sha256"]), str(row["tract_id"])), []).append(
            row
        )

    output: list[dict[str, Any]] = []
    for key in sorted(grouped):
        rows = grouped[key]
        first = rows[0]
        for row in rows[1:]:
            if (
                row["validation_case_id"] != first["validation_case_id"]
                or row["amplicon_id"] != first["amplicon_id"]
                or row["orientation"] != first["orientation"]
                or row["interrupt_aligned_base"] != first["interrupt_aligned_base"]
            ):
                raise ValueError(
                    f"{key}: window metadata changes across one read/tract"
                )

        impurities = [float(row["mean_profile_impurity"]) for row in rows]
        shifted_max = optional_values(rows, "candidate_shifted_reference_mass_max")
        residual_min = optional_values(rows, "candidate_residual_mass_min")
        explainability = optional_values(
            rows,
            "candidate_explainable_nonzero_fraction_max",
        )
        shifted_ranges = optional_values(
            rows,
            "candidate_shifted_reference_mass_range",
        )
        residual_ranges = optional_values(rows, "candidate_residual_mass_range")
        output.append(
            {
                "validation_case_id": first["validation_case_id"],
                "read_sha256": first["read_sha256"],
                "tract_id": first["tract_id"],
                "amplicon_id": first["amplicon_id"],
                "orientation": first["orientation"],
                "interrupt_aligned_base": first["interrupt_aligned_base"],
                "windows": len(rows),
                "windows_without_informative_candidates": sum(
                    int(row["informative_candidates"]) == 0 for row in rows
                ),
                "windows_without_explainability_candidates": sum(
                    int(row["explainability_candidates"]) == 0 for row in rows
                ),
                "mean_window_profile_impurity": mean(impurities),
                "max_window_profile_impurity": max(impurities),
                "mean_window_noisy_fraction": mean(
                    [float(row["noisy_fraction"]) for row in rows]
                ),
                "mean_candidate_shifted_reference_mass_max": mean_or_none(shifted_max),
                "max_candidate_shifted_reference_mass_max": max_or_none(shifted_max),
                "mean_candidate_residual_mass_min": mean_or_none(residual_min),
                "max_candidate_residual_mass_min": max_or_none(residual_min),
                "mean_candidate_explainable_nonzero_fraction_max": mean_or_none(
                    explainability
                ),
                "min_candidate_explainable_nonzero_fraction_max": min_or_none(
                    explainability
                ),
                "mean_candidate_shifted_reference_mass_range": mean_or_none(
                    shifted_ranges
                ),
                "mean_candidate_residual_mass_range": mean_or_none(residual_ranges),
            }
        )
    return output


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


def write_rows(
    path: Path,
    rows: list[dict[str, Any]],
    columns: tuple[str, ...],
    label: str,
) -> None:
    with path.open("x", encoding="utf-8", newline="") as target:
        built = writer(target, columns)
        for index, row in enumerate(rows):
            if set(row) != set(columns):
                raise ValueError(f"{label} row {index} does not match output columns")
            built.writerow({key: csv_value(row[key]) for key in columns})
        target.flush()
        os.fsync(target.fileno())


def output_index(
    source_dir: Path,
    source_index: dict[str, Any],
    offsets: tuple[int, ...],
    windows_path: Path,
    reads_path: Path,
    windows_count: int,
    reads_count: int,
) -> dict[str, Any]:
    return {
        "schema_version": PHASE_EXPLAINABILITY_SCHEMA_VERSION,
        "source_phase_hypotheses_sha256": file_sha256(source_dir / "index.json"),
        "source_polyc_phase_sha256": source_index["source_polyc_phase_sha256"],
        "source_corpus_sha256": source_index["source_corpus_sha256"],
        "signal_version": source_index["signal_version"],
        "manifest_sha256": source_index["manifest_sha256"],
        "reference_sha256": source_index["reference_sha256"],
        "configuration_sha256": source_index["configuration_sha256"],
        "method": {
            "candidate_offsets": list(offsets),
            "candidate_envelope": (
                "extrema and ranges across informative source candidates; no candidate "
                "identity is retained for any extremum"
            ),
            "explainable_nonzero_fraction": (
                "shifted_reference_mass / (shifted_reference_mass + residual_mass) "
                "for candidates with positive non-zero mass"
            ),
            "read_aggregation": "window-weighted descriptive summaries per read/tract",
            "candidate_selection": "none; no winning offset or identity is emitted",
            "thresholds": "none",
        },
        "windows_file": "windows.csv",
        "windows_sha256": file_sha256(windows_path),
        "windows_rows": windows_count,
        "windows_columns": list(WINDOW_COLUMNS),
        "reads_file": "reads.csv",
        "reads_sha256": file_sha256(reads_path),
        "reads_rows": reads_count,
        "reads_columns": list(READ_COLUMNS),
    }


def publish_phase_explainability(source_dir: Path, output_dir: Path) -> None:
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

    envelope_rows = build_envelopes(windows, candidates, offsets)
    windows_output = [window_row(item) for item in envelope_rows]
    reads_output = read_rows(windows_output)

    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        windows_path = stage / "windows.csv"
        reads_path = stage / "reads.csv"
        write_rows(windows_path, windows_output, WINDOW_COLUMNS, "window")
        write_rows(reads_path, reads_output, READ_COLUMNS, "read")
        write_json(
            stage / "index.json",
            output_index(
                source_dir,
                source_index,
                offsets,
                windows_path,
                reads_path,
                len(windows_output),
                len(reads_output),
            ),
        )
        sync_directory(stage)

        try:
            output_dir.mkdir()
        except FileExistsError as error:
            raise FileExistsError(
                "output directory appeared while phase explainability was running: "
                f"{output_dir}"
            ) from error
        try:
            for name in ("windows.csv", "reads.csv", "index.json"):
                os.rename(stage / name, output_dir / name)
            sync_directory(output_dir)
            sync_directory(output_dir.parent)
        except OSError:
            shutil.rmtree(output_dir, ignore_errors=True)
            sync_directory(output_dir.parent)
            raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
