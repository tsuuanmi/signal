"""Development-only characterization of phase evidence around biological errors."""

from __future__ import annotations

import csv
import math
import os
import shutil
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any, TextIO

from .filesystem import file_sha256, sync_directory, validate_new_directory, write_json
from .model import (
    PHASE_ERROR_CHARACTERIZATION_SCHEMA_VERSION,
    PHASE_INTERPRETATION_DATASET_SCHEMA_VERSION,
    VARIANT_PHASE_CONTEXT_SCHEMA_VERSION,
)
from .phase_artifact import CandidateRecord, WindowRecord, csv_int, optional_unit_float, unit_float
from .phase_hypotheses import HYPOTHESIS_COLUMNS
from .phase_interpretation_dataset import DEVELOPMENT_WINDOW_COLUMNS
from .research_loader import json_object, strict_keys
from .variant_phase_context import (
    DIFFERENCE_COLUMNS_OUT,
    WINDOW_COLUMNS as CONTEXT_WINDOW_COLUMNS,
)

INTERPRETATION_INDEX_FIELDS = (
    "schema_version",
    "source_corpus_sha256",
    "source_phase_hypotheses_sha256",
    "source_polyc_phase_sha256",
    "signal_version",
    "manifest_sha256",
    "reference_sha256",
    "configuration_sha256",
    "partition_groups",
    "method",
    "partition_summary",
    "development_windows_file",
    "development_windows_sha256",
    "development_windows_rows",
    "development_windows_columns",
    "development_candidates_file",
    "development_candidates_sha256",
    "development_candidates_rows",
    "development_candidates_columns",
    "readiness_file",
    "readiness_sha256",
    "readiness_rows",
    "readiness_columns",
)

CONTEXT_INDEX_FIELDS = (
    "schema_version",
    "source_variant_profile_evaluation_sha256",
    "source_corpus_sha256",
    "source_polyc_phase_sha256",
    "source_phase_hypotheses_sha256",
    "signal_version",
    "manifest_sha256",
    "reference_sha256",
    "configuration_sha256",
    "partitions",
    "method",
    "differences_file",
    "differences_sha256",
    "differences_rows",
    "differences_columns",
    "observations_file",
    "observations_sha256",
    "observations_rows",
    "observations_columns",
    "windows_file",
    "windows_sha256",
    "windows_rows",
    "windows_columns",
    "candidates_file",
    "candidates_sha256",
    "candidates_rows",
    "candidates_columns",
    "readiness_file",
    "readiness_sha256",
    "readiness_rows",
    "readiness_columns",
)

CANDIDATE_COLUMNS = (
    "window_id",
    "validation_case_id",
    "source_group_id",
    "read_sha256",
    "tract_id",
    "orientation",
    "amplicon_id",
    "sequencing_run_id",
    "start_distance_after_tract",
    "overlap_context",
    "overlapping_biological_differences",
    "overlapping_extra_differences",
    "overlapping_missing_differences",
    "reference_offset_in_read_order",
    "informative_positions",
    "mean_zero_reference_mass",
    "mean_shifted_reference_mass",
    "mean_residual_mass",
    "nonzero_mass",
    "structured_fraction",
)

WINDOW_COLUMNS = (
    "window_id",
    "validation_case_id",
    "source_group_id",
    "specimen_group_id",
    "read_sha256",
    "pcr_replicate_id",
    "sequencing_run_id",
    "instrument_id",
    "amplicon_id",
    "orientation",
    "tract_id",
    "interrupt_aligned_base",
    "start_distance_after_tract",
    "end_distance_after_tract",
    "profile_observations",
    "noisy_observations",
    "noisy_fraction",
    "mean_profile_impurity",
    "mean_zero_reference_mass",
    "overlap_context",
    "overlapping_biological_differences",
    "overlapping_extra_differences",
    "overlapping_missing_differences",
    "candidate_count",
    "informative_candidates",
    "nonzero_candidates",
    "max_informative_positions",
    "mean_informative_positions",
    "candidate_shifted_mass_min",
    "candidate_shifted_mass_max",
    "candidate_shifted_mass_range",
    "candidate_residual_mass_min",
    "candidate_residual_mass_max",
    "candidate_residual_mass_range",
    "candidate_nonzero_mass_min",
    "candidate_nonzero_mass_max",
    "candidate_nonzero_mass_range",
    "candidate_structured_fraction_min",
    "candidate_structured_fraction_max",
    "candidate_structured_fraction_range",
)

TRANSITION_COLUMNS = (
    "validation_case_id",
    "source_group_id",
    "read_sha256",
    "tract_id",
    "orientation",
    "amplicon_id",
    "sequencing_run_id",
    "left_window_id",
    "right_window_id",
    "left_start_distance_after_tract",
    "right_start_distance_after_tract",
    "start_distance_delta",
    "left_overlap_context",
    "right_overlap_context",
    "left_mean_zero_reference_mass",
    "right_mean_zero_reference_mass",
    "zero_reference_mass_delta",
    "left_mean_profile_impurity",
    "right_mean_profile_impurity",
    "profile_impurity_delta",
    "left_noisy_fraction",
    "right_noisy_fraction",
    "noisy_fraction_delta",
    "left_candidate_shifted_mass_max",
    "right_candidate_shifted_mass_max",
    "candidate_shifted_mass_max_delta",
    "left_candidate_residual_mass_min",
    "right_candidate_residual_mass_min",
    "candidate_residual_mass_min_delta",
    "left_candidate_nonzero_mass_max",
    "right_candidate_nonzero_mass_max",
    "candidate_nonzero_mass_max_delta",
    "left_candidate_structured_fraction_max",
    "right_candidate_structured_fraction_max",
    "candidate_structured_fraction_max_delta",
)

STRATA_COLUMNS = (
    "overlap_context",
    "tract_id",
    "orientation",
    "amplicon_id",
    "sequencing_run_id",
    "cases",
    "source_groups",
    "reads",
    "read_tracts",
    "windows",
    "biological_differences",
    "mean_zero_reference_mass",
    "mean_profile_impurity",
    "mean_noisy_fraction",
    "mean_candidate_shifted_mass_max",
    "mean_candidate_residual_mass_min",
    "mean_candidate_nonzero_mass_max",
    "mean_candidate_structured_fraction_max",
)


@dataclass(frozen=True)
class PreparedWindow:
    source: dict[str, str]
    record: WindowRecord


@dataclass(frozen=True)
class CandidateFeatures:
    source: CandidateRecord
    nonzero_mass: float | None
    structured_fraction: float | None


@dataclass(frozen=True)
class WindowFeatures:
    window: PreparedWindow
    difference_ids: frozenset[str]
    extra_ids: frozenset[str]
    missing_ids: frozenset[str]
    candidates: tuple[CandidateFeatures, ...]
    informative_candidates: int
    nonzero_candidates: int
    max_informative_positions: int
    mean_informative_positions: float | None
    shifted_min: float | None
    shifted_max: float | None
    residual_min: float | None
    residual_max: float | None
    nonzero_min: float | None
    nonzero_max: float | None
    structured_min: float | None
    structured_max: float | None

    @property
    def overlap_context(self) -> str:
        if self.extra_ids and self.missing_ids:
            return "extra+missing"
        if self.extra_ids:
            return "extra"
        if self.missing_ids:
            return "missing"
        return "none"


def mean(values: list[float]) -> float:
    return math.fsum(values) / len(values)


def mean_or_none(values: list[float]) -> float | None:
    return mean(values) if values else None


def value_range(low: float | None, high: float | None) -> float | None:
    if low is None or high is None:
        return None
    return high - low


def delta(left: Any, right: Any) -> float | None:
    if left is None or right is None:
        return None
    return float(right) - float(left)


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


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


def index_count(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def load_csv(
    path: Path,
    columns: tuple[str, ...],
    expected_rows: int,
    expected_sha256: str,
    label: str,
) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"{label} is not a regular file: {path}")
    if file_sha256(path) != expected_sha256:
        raise ValueError(f"{label} SHA-256 mismatch")
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or tuple(reader.fieldnames) != columns:
            raise ValueError(f"{label} columns differ from current contract")
        rows = list(reader)
    if len(rows) != expected_rows:
        raise ValueError(
            f"{label} expected {expected_rows} rows, found {len(rows)}"
        )
    return rows


def load_interpretation(
    source_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, str]]]:
    index_path = source_dir / "index.json"
    if not index_path.is_file():
        raise ValueError(f"phase interpretation index is missing: {index_path}")
    index = json_object(index_path)
    strict_keys(index, INTERPRETATION_INDEX_FIELDS, "phase interpretation index")
    if index["schema_version"] != PHASE_INTERPRETATION_DATASET_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported phase interpretation schema: {index['schema_version']!r}"
        )
    if index["development_windows_file"] != "development-windows.csv":
        raise ValueError("development_windows_file must be development-windows.csv")
    if index["development_candidates_file"] != "development-candidates.csv":
        raise ValueError(
            "development_candidates_file must be development-candidates.csv"
        )
    if index["development_windows_columns"] != list(DEVELOPMENT_WINDOW_COLUMNS):
        raise ValueError("development window columns differ from current contract")
    if index["development_candidates_columns"] != list(HYPOTHESIS_COLUMNS):
        raise ValueError("development candidate columns differ from current contract")

    windows = load_csv(
        source_dir / "development-windows.csv",
        DEVELOPMENT_WINDOW_COLUMNS,
        index_count(index["development_windows_rows"], "development_windows_rows"),
        str(index["development_windows_sha256"]),
        "development windows",
    )
    candidates = load_csv(
        source_dir / "development-candidates.csv",
        HYPOTHESIS_COLUMNS,
        index_count(
            index["development_candidates_rows"],
            "development_candidates_rows",
        ),
        str(index["development_candidates_sha256"]),
        "development candidates",
    )
    return index, windows, candidates


def load_context(
    source_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, str]]]:
    index_path = source_dir / "index.json"
    if not index_path.is_file():
        raise ValueError(f"variant phase context index is missing: {index_path}")
    index = json_object(index_path)
    strict_keys(index, CONTEXT_INDEX_FIELDS, "variant phase context index")
    if index["schema_version"] != VARIANT_PHASE_CONTEXT_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported variant phase context schema: {index['schema_version']!r}"
        )
    if index["differences_file"] != "differences.csv":
        raise ValueError("variant phase context differences_file must be differences.csv")
    if index["windows_file"] != "windows.csv":
        raise ValueError("variant phase context windows_file must be windows.csv")
    if index["differences_columns"] != list(DIFFERENCE_COLUMNS_OUT):
        raise ValueError("variant phase context difference columns differ from contract")
    if index["windows_columns"] != list(CONTEXT_WINDOW_COLUMNS):
        raise ValueError("variant phase context window columns differ from contract")

    differences = load_csv(
        source_dir / "differences.csv",
        DIFFERENCE_COLUMNS_OUT,
        index_count(index["differences_rows"], "differences_rows"),
        str(index["differences_sha256"]),
        "variant phase differences",
    )
    windows = load_csv(
        source_dir / "windows.csv",
        CONTEXT_WINDOW_COLUMNS,
        index_count(index["windows_rows"], "windows_rows"),
        str(index["windows_sha256"]),
        "variant phase windows",
    )
    return index, differences, windows


def validate_provenance(
    interpretation_index: dict[str, Any],
    context_index: dict[str, Any],
) -> None:
    for key in (
        "source_corpus_sha256",
        "source_polyc_phase_sha256",
        "source_phase_hypotheses_sha256",
        "signal_version",
        "manifest_sha256",
        "reference_sha256",
        "configuration_sha256",
    ):
        if interpretation_index[key] != context_index[key]:
            raise ValueError(f"{key} differs between development research artifacts")
    if interpretation_index["partition_groups"] != context_index["partitions"]:
        raise ValueError("partition declarations differ between research artifacts")


def parse_window(row: dict[str, str], line: int) -> PreparedWindow:
    label = f"development-windows.csv:{line}"
    if row["include_in_threshold_fit"] != "true":
        raise ValueError(f"{label}: non-fit window in development dataset")
    required = (
        "window_id",
        "validation_case_id",
        "source_group_id",
        "read_sha256",
        "tract_id",
        "orientation",
    )
    if any(not row[field] for field in required):
        raise ValueError(f"{label}: missing window identity")
    orientation = row["orientation"]
    if orientation not in {"forward", "reverse"}:
        raise ValueError(f"{label}.orientation must be forward or reverse")
    start = csv_int(row["start_distance_after_tract"], f"{label}.start_distance", 1)
    end = csv_int(row["end_distance_after_tract"], f"{label}.end_distance", 1)
    if end < start:
        raise ValueError(f"{label}: end distance precedes start")
    profile_observations = csv_int(
        row["profile_observations"],
        f"{label}.profile_observations",
        1,
    )
    noisy_observations = csv_int(
        row["noisy_observations"],
        f"{label}.noisy_observations",
        0,
    )
    if noisy_observations > profile_observations:
        raise ValueError(f"{label}: noisy observations exceed profile observations")
    record = WindowRecord(
        window_id=row["window_id"],
        validation_case_id=row["validation_case_id"],
        read_sha256=row["read_sha256"],
        tract_id=row["tract_id"],
        amplicon_id=row["amplicon_id"],
        orientation=orientation,
        interrupt_aligned_base=row["interrupt_aligned_base"],
        start_distance=start,
        end_distance=end,
        start_call_index=csv_int(
            row["start_call_index_0based"],
            f"{label}.start_call_index",
            0,
        ),
        end_call_index=csv_int(
            row["end_call_index_0based"],
            f"{label}.end_call_index",
            0,
        ),
        profile_observations=profile_observations,
        noisy_observations=noisy_observations,
        mean_profile_impurity=unit_float(
            row["mean_profile_impurity"],
            f"{label}.mean_profile_impurity",
        ),
        mean_zero_reference_mass=unit_float(
            row["mean_zero_reference_mass"],
            f"{label}.mean_zero_reference_mass",
        ),
    )
    return PreparedWindow(source=row, record=record)


def parse_candidate(row: dict[str, str], line: int) -> CandidateRecord:
    label = f"development-candidates.csv:{line}"
    if not row["window_id"]:
        raise ValueError(f"{label}: missing window_id")
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
            raise ValueError(f"{label}: zero-informative candidate has mass")
    elif any(value is None for value in (zero, shifted, residual)):
        raise ValueError(f"{label}: informative candidate is missing mass")
    return CandidateRecord(
        window_id=row["window_id"],
        offset=csv_int(
            row["reference_offset_in_read_order"],
            f"{label}.reference_offset",
        ),
        informative_positions=informative,
        zero_mass=zero,
        shifted_mass=shifted,
        residual_mass=residual,
    )


def candidate_features(candidate: CandidateRecord) -> CandidateFeatures:
    if candidate.shifted_mass is None or candidate.residual_mass is None:
        return CandidateFeatures(candidate, None, None)
    nonzero = candidate.shifted_mass + candidate.residual_mass
    structured = candidate.shifted_mass / nonzero if nonzero > 0.0 else None
    return CandidateFeatures(candidate, nonzero, structured)


def overlap_annotations(
    differences: list[dict[str, str]],
    links: list[dict[str, str]],
    known_windows: set[str],
) -> dict[str, tuple[frozenset[str], frozenset[str], frozenset[str]]]:
    difference_kind: dict[str, str] = {}
    for row in differences:
        difference_id = row["difference_id"]
        kind = row["difference"]
        if not difference_id or kind not in {"extra", "missing"}:
            raise ValueError("variant phase difference identity/type is invalid")
        previous = difference_kind.setdefault(difference_id, kind)
        if previous != kind:
            raise ValueError(f"{difference_id}: difference type changes")

    by_window: dict[str, set[str]] = defaultdict(set)
    for row in links:
        difference_id = row["difference_id"]
        window_id = row["window_id"]
        if difference_id not in difference_kind:
            raise ValueError(f"{window_id}: unknown biological difference")
        if window_id not in known_windows:
            raise ValueError(
                f"{window_id}: context window is absent from development dataset"
            )
        by_window[window_id].add(difference_id)

    output: dict[
        str,
        tuple[frozenset[str], frozenset[str], frozenset[str]],
    ] = {}
    for window_id, ids in by_window.items():
        extra = frozenset(
            difference_id
            for difference_id in ids
            if difference_kind[difference_id] == "extra"
        )
        missing = frozenset(
            difference_id
            for difference_id in ids
            if difference_kind[difference_id] == "missing"
        )
        output[window_id] = (frozenset(ids), extra, missing)
    return output


def summarize_window(
    window: PreparedWindow,
    difference_ids: frozenset[str],
    extra_ids: frozenset[str],
    missing_ids: frozenset[str],
    candidates: list[CandidateFeatures],
) -> WindowFeatures:
    informative = [
        item for item in candidates if item.source.informative_positions > 0
    ]
    shifted = [
        float(item.source.shifted_mass)
        for item in informative
        if item.source.shifted_mass is not None
    ]
    residual = [
        float(item.source.residual_mass)
        for item in informative
        if item.source.residual_mass is not None
    ]
    nonzero = [
        float(item.nonzero_mass)
        for item in informative
        if item.nonzero_mass is not None
    ]
    structured = [
        float(item.structured_fraction)
        for item in informative
        if item.structured_fraction is not None
    ]
    if len(shifted) != len(informative) or len(residual) != len(informative):
        raise ValueError(
            f"{window.record.window_id}: informative candidate mass is missing"
        )
    return WindowFeatures(
        window=window,
        difference_ids=difference_ids,
        extra_ids=extra_ids,
        missing_ids=missing_ids,
        candidates=tuple(candidates),
        informative_candidates=len(informative),
        nonzero_candidates=len(structured),
        max_informative_positions=max(
            (item.source.informative_positions for item in informative),
            default=0,
        ),
        mean_informative_positions=mean_or_none(
            [float(item.source.informative_positions) for item in informative]
        ),
        shifted_min=min(shifted) if shifted else None,
        shifted_max=max(shifted) if shifted else None,
        residual_min=min(residual) if residual else None,
        residual_max=max(residual) if residual else None,
        nonzero_min=min(nonzero) if nonzero else None,
        nonzero_max=max(nonzero) if nonzero else None,
        structured_min=min(structured) if structured else None,
        structured_max=max(structured) if structured else None,
    )


def build_features(
    window_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
    differences: list[dict[str, str]],
    links: list[dict[str, str]],
) -> list[WindowFeatures]:
    windows: dict[str, PreparedWindow] = {}
    for line, row in enumerate(window_rows, start=2):
        parsed = parse_window(row, line)
        window_id = parsed.record.window_id
        if window_id in windows:
            raise ValueError(f"duplicate development window: {window_id}")
        windows[window_id] = parsed

    grouped_candidates: dict[str, list[CandidateFeatures]] = defaultdict(list)
    seen_candidates: set[tuple[str, int]] = set()
    for line, row in enumerate(candidate_rows, start=2):
        candidate = parse_candidate(row, line)
        if candidate.window_id not in windows:
            raise ValueError(
                f"{candidate.window_id}: candidate references unknown development window"
            )
        key = (candidate.window_id, candidate.offset)
        if key in seen_candidates:
            raise ValueError(f"duplicate development candidate: {key}")
        seen_candidates.add(key)
        grouped_candidates[candidate.window_id].append(candidate_features(candidate))

    annotations = overlap_annotations(differences, links, set(windows))
    output: list[WindowFeatures] = []
    for window_id in sorted(
        windows,
        key=lambda value: (
            windows[value].record.validation_case_id,
            windows[value].record.read_sha256,
            windows[value].record.tract_id,
            windows[value].record.start_distance,
            value,
        ),
    ):
        candidates = sorted(
            grouped_candidates.get(window_id, []),
            key=lambda item: item.source.offset,
        )
        if not candidates:
            raise ValueError(f"{window_id}: development window has no candidates")
        ids, extra, missing = annotations.get(
            window_id,
            (frozenset(), frozenset(), frozenset()),
        )
        output.append(
            summarize_window(
                windows[window_id],
                ids,
                extra,
                missing,
                candidates,
            )
        )
    return output


def candidate_rows(features: list[WindowFeatures]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in features:
        window = item.window.record
        source = item.window.source
        for candidate in item.candidates:
            output.append(
                {
                    "window_id": window.window_id,
                    "validation_case_id": window.validation_case_id,
                    "source_group_id": source["source_group_id"],
                    "read_sha256": window.read_sha256,
                    "tract_id": window.tract_id,
                    "orientation": window.orientation,
                    "amplicon_id": window.amplicon_id,
                    "sequencing_run_id": source["sequencing_run_id"],
                    "start_distance_after_tract": window.start_distance,
                    "overlap_context": item.overlap_context,
                    "overlapping_biological_differences": len(item.difference_ids),
                    "overlapping_extra_differences": len(item.extra_ids),
                    "overlapping_missing_differences": len(item.missing_ids),
                    "reference_offset_in_read_order": candidate.source.offset,
                    "informative_positions": candidate.source.informative_positions,
                    "mean_zero_reference_mass": candidate.source.zero_mass,
                    "mean_shifted_reference_mass": candidate.source.shifted_mass,
                    "mean_residual_mass": candidate.source.residual_mass,
                    "nonzero_mass": candidate.nonzero_mass,
                    "structured_fraction": candidate.structured_fraction,
                }
            )
    return output


def window_row(item: WindowFeatures) -> dict[str, Any]:
    window = item.window.record
    source = item.window.source
    return {
        "window_id": window.window_id,
        "validation_case_id": window.validation_case_id,
        "source_group_id": source["source_group_id"],
        "specimen_group_id": source["specimen_group_id"],
        "read_sha256": window.read_sha256,
        "pcr_replicate_id": source["pcr_replicate_id"],
        "sequencing_run_id": source["sequencing_run_id"],
        "instrument_id": source["instrument_id"],
        "amplicon_id": window.amplicon_id,
        "orientation": window.orientation,
        "tract_id": window.tract_id,
        "interrupt_aligned_base": window.interrupt_aligned_base,
        "start_distance_after_tract": window.start_distance,
        "end_distance_after_tract": window.end_distance,
        "profile_observations": window.profile_observations,
        "noisy_observations": window.noisy_observations,
        "noisy_fraction": window.noisy_observations / window.profile_observations,
        "mean_profile_impurity": window.mean_profile_impurity,
        "mean_zero_reference_mass": window.mean_zero_reference_mass,
        "overlap_context": item.overlap_context,
        "overlapping_biological_differences": len(item.difference_ids),
        "overlapping_extra_differences": len(item.extra_ids),
        "overlapping_missing_differences": len(item.missing_ids),
        "candidate_count": len(item.candidates),
        "informative_candidates": item.informative_candidates,
        "nonzero_candidates": item.nonzero_candidates,
        "max_informative_positions": item.max_informative_positions,
        "mean_informative_positions": item.mean_informative_positions,
        "candidate_shifted_mass_min": item.shifted_min,
        "candidate_shifted_mass_max": item.shifted_max,
        "candidate_shifted_mass_range": value_range(item.shifted_min, item.shifted_max),
        "candidate_residual_mass_min": item.residual_min,
        "candidate_residual_mass_max": item.residual_max,
        "candidate_residual_mass_range": value_range(item.residual_min, item.residual_max),
        "candidate_nonzero_mass_min": item.nonzero_min,
        "candidate_nonzero_mass_max": item.nonzero_max,
        "candidate_nonzero_mass_range": value_range(item.nonzero_min, item.nonzero_max),
        "candidate_structured_fraction_min": item.structured_min,
        "candidate_structured_fraction_max": item.structured_max,
        "candidate_structured_fraction_range": value_range(
            item.structured_min,
            item.structured_max,
        ),
    }


def transition_rows(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in windows:
        grouped[(str(row["read_sha256"]), str(row["tract_id"]))].append(row)

    output: list[dict[str, Any]] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda row: (
                int(row["start_distance_after_tract"]),
                str(row["window_id"]),
            ),
        )
        starts = [int(row["start_distance_after_tract"]) for row in ordered]
        if len(starts) != len(set(starts)):
            raise ValueError(f"{key}: duplicate development window start distance")
        first = ordered[0]
        for row in ordered[1:]:
            for field in (
                "validation_case_id",
                "source_group_id",
                "orientation",
                "amplicon_id",
                "sequencing_run_id",
            ):
                if row[field] != first[field]:
                    raise ValueError(f"{key}: {field} changes across read/tract")

        for left, right in pairwise(ordered):
            output.append(
                {
                    "validation_case_id": left["validation_case_id"],
                    "source_group_id": left["source_group_id"],
                    "read_sha256": left["read_sha256"],
                    "tract_id": left["tract_id"],
                    "orientation": left["orientation"],
                    "amplicon_id": left["amplicon_id"],
                    "sequencing_run_id": left["sequencing_run_id"],
                    "left_window_id": left["window_id"],
                    "right_window_id": right["window_id"],
                    "left_start_distance_after_tract": left[
                        "start_distance_after_tract"
                    ],
                    "right_start_distance_after_tract": right[
                        "start_distance_after_tract"
                    ],
                    "start_distance_delta": int(
                        right["start_distance_after_tract"]
                    )
                    - int(left["start_distance_after_tract"]),
                    "left_overlap_context": left["overlap_context"],
                    "right_overlap_context": right["overlap_context"],
                    "left_mean_zero_reference_mass": left[
                        "mean_zero_reference_mass"
                    ],
                    "right_mean_zero_reference_mass": right[
                        "mean_zero_reference_mass"
                    ],
                    "zero_reference_mass_delta": delta(
                        left["mean_zero_reference_mass"],
                        right["mean_zero_reference_mass"],
                    ),
                    "left_mean_profile_impurity": left["mean_profile_impurity"],
                    "right_mean_profile_impurity": right["mean_profile_impurity"],
                    "profile_impurity_delta": delta(
                        left["mean_profile_impurity"],
                        right["mean_profile_impurity"],
                    ),
                    "left_noisy_fraction": left["noisy_fraction"],
                    "right_noisy_fraction": right["noisy_fraction"],
                    "noisy_fraction_delta": delta(
                        left["noisy_fraction"],
                        right["noisy_fraction"],
                    ),
                    "left_candidate_shifted_mass_max": left[
                        "candidate_shifted_mass_max"
                    ],
                    "right_candidate_shifted_mass_max": right[
                        "candidate_shifted_mass_max"
                    ],
                    "candidate_shifted_mass_max_delta": delta(
                        left["candidate_shifted_mass_max"],
                        right["candidate_shifted_mass_max"],
                    ),
                    "left_candidate_residual_mass_min": left[
                        "candidate_residual_mass_min"
                    ],
                    "right_candidate_residual_mass_min": right[
                        "candidate_residual_mass_min"
                    ],
                    "candidate_residual_mass_min_delta": delta(
                        left["candidate_residual_mass_min"],
                        right["candidate_residual_mass_min"],
                    ),
                    "left_candidate_nonzero_mass_max": left[
                        "candidate_nonzero_mass_max"
                    ],
                    "right_candidate_nonzero_mass_max": right[
                        "candidate_nonzero_mass_max"
                    ],
                    "candidate_nonzero_mass_max_delta": delta(
                        left["candidate_nonzero_mass_max"],
                        right["candidate_nonzero_mass_max"],
                    ),
                    "left_candidate_structured_fraction_max": left[
                        "candidate_structured_fraction_max"
                    ],
                    "right_candidate_structured_fraction_max": right[
                        "candidate_structured_fraction_max"
                    ],
                    "candidate_structured_fraction_max_delta": delta(
                        left["candidate_structured_fraction_max"],
                        right["candidate_structured_fraction_max"],
                    ),
                }
            )
    return output


def strata_rows(
    windows: list[dict[str, Any]],
    features: list[WindowFeatures],
) -> list[dict[str, Any]]:
    differences_by_window = {
        item.window.record.window_id: item.difference_ids for item in features
    }
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in windows:
        key = (
            str(row["overlap_context"]),
            str(row["tract_id"]),
            str(row["orientation"]),
            str(row["amplicon_id"]),
            str(row["sequencing_run_id"]),
        )
        grouped[key].append(row)

    output: list[dict[str, Any]] = []
    for key in sorted(grouped):
        rows = grouped[key]
        overlap_context, tract_id, orientation, amplicon_id, sequencing_run_id = key
        difference_ids: set[str] = set()
        for row in rows:
            difference_ids.update(differences_by_window[str(row["window_id"])])
        optional_fields = (
            "candidate_shifted_mass_max",
            "candidate_residual_mass_min",
            "candidate_nonzero_mass_max",
            "candidate_structured_fraction_max",
        )
        optional_means = {
            field: mean_or_none(
                [float(row[field]) for row in rows if row[field] is not None]
            )
            for field in optional_fields
        }
        output.append(
            {
                "overlap_context": overlap_context,
                "tract_id": tract_id,
                "orientation": orientation,
                "amplicon_id": amplicon_id,
                "sequencing_run_id": sequencing_run_id,
                "cases": len({str(row["validation_case_id"]) for row in rows}),
                "source_groups": len({str(row["source_group_id"]) for row in rows}),
                "reads": len({str(row["read_sha256"]) for row in rows}),
                "read_tracts": len(
                    {
                        (str(row["read_sha256"]), str(row["tract_id"]))
                        for row in rows
                    }
                ),
                "windows": len(rows),
                "biological_differences": len(difference_ids),
                "mean_zero_reference_mass": mean(
                    [float(row["mean_zero_reference_mass"]) for row in rows]
                ),
                "mean_profile_impurity": mean(
                    [float(row["mean_profile_impurity"]) for row in rows]
                ),
                "mean_noisy_fraction": mean(
                    [float(row["noisy_fraction"]) for row in rows]
                ),
                "mean_candidate_shifted_mass_max": optional_means[
                    "candidate_shifted_mass_max"
                ],
                "mean_candidate_residual_mass_min": optional_means[
                    "candidate_residual_mass_min"
                ],
                "mean_candidate_nonzero_mass_max": optional_means[
                    "candidate_nonzero_mass_max"
                ],
                "mean_candidate_structured_fraction_max": optional_means[
                    "candidate_structured_fraction_max"
                ],
            }
        )
    return output


def output_index(
    interpretation_dir: Path,
    interpretation_index: dict[str, Any],
    context_dir: Path,
    context_index: dict[str, Any],
    paths: dict[str, Path],
    counts: dict[str, int],
) -> dict[str, Any]:
    return {
        "schema_version": PHASE_ERROR_CHARACTERIZATION_SCHEMA_VERSION,
        "source_phase_interpretation_dataset_sha256": file_sha256(
            interpretation_dir / "index.json"
        ),
        "source_variant_phase_context_sha256": file_sha256(context_dir / "index.json"),
        "source_variant_profile_evaluation_sha256": context_index[
            "source_variant_profile_evaluation_sha256"
        ],
        "source_corpus_sha256": interpretation_index["source_corpus_sha256"],
        "source_polyc_phase_sha256": interpretation_index["source_polyc_phase_sha256"],
        "source_phase_hypotheses_sha256": interpretation_index[
            "source_phase_hypotheses_sha256"
        ],
        "signal_version": interpretation_index["signal_version"],
        "manifest_sha256": interpretation_index["manifest_sha256"],
        "reference_sha256": interpretation_index["reference_sha256"],
        "configuration_sha256": interpretation_index["configuration_sha256"],
        "partition_groups": interpretation_index["partition_groups"],
        "method": {
            "scope": (
                "fit-eligible development windows only; no continuous holdout evidence"
            ),
            "error_annotation": (
                "exact window membership from signal.validation_variant_phase_context/v1; "
                "representation disagreements excluded upstream"
            ),
            "none_context_semantics": (
                "window has no exact biological missing/extra disagreement overlap; "
                "not a clean or true-negative label"
            ),
            "candidate_features": (
                "nonzero_mass=shifted+residual and structured_fraction="
                "shifted/nonzero for positive nonzero mass"
            ),
            "candidate_envelope": (
                "descriptive extrema/ranges across informative candidates; no candidate "
                "identity retained for extrema"
            ),
            "trajectory": (
                "signed deltas between consecutive source windows for one read/tract"
            ),
            "candidate_selection": "none",
            "thresholds": "none",
            "interpretation": "none; no state, persistence, or recovery rule",
        },
        "candidates_file": "candidates.csv",
        "candidates_sha256": file_sha256(paths["candidates"]),
        "candidates_rows": counts["candidates"],
        "candidates_columns": list(CANDIDATE_COLUMNS),
        "windows_file": "windows.csv",
        "windows_sha256": file_sha256(paths["windows"]),
        "windows_rows": counts["windows"],
        "windows_columns": list(WINDOW_COLUMNS),
        "transitions_file": "transitions.csv",
        "transitions_sha256": file_sha256(paths["transitions"]),
        "transitions_rows": counts["transitions"],
        "transitions_columns": list(TRANSITION_COLUMNS),
        "strata_file": "strata.csv",
        "strata_sha256": file_sha256(paths["strata"]),
        "strata_rows": counts["strata"],
        "strata_columns": list(STRATA_COLUMNS),
    }


def publish_phase_error_characterization(
    interpretation_dir: Path,
    context_dir: Path,
    output_dir: Path,
) -> None:
    interpretation_dir = interpretation_dir.resolve()
    context_dir = context_dir.resolve()
    output_dir = output_dir.resolve()
    for label, path in (
        ("phase interpretation dataset", interpretation_dir),
        ("variant phase context", context_dir),
    ):
        if not path.is_dir():
            raise ValueError(f"{label} directory does not exist: {path}")
    validate_new_directory(output_dir, (interpretation_dir, context_dir))
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if not output_dir.parent.is_dir() or output_dir.parent.is_symlink():
        raise ValueError(
            f"output parent is not a regular directory: {output_dir.parent}"
        )

    interpretation_index, window_source, candidate_source = load_interpretation(
        interpretation_dir
    )
    context_index, differences, links = load_context(context_dir)
    validate_provenance(interpretation_index, context_index)

    features = build_features(window_source, candidate_source, differences, links)
    candidate_output = candidate_rows(features)
    window_output = [window_row(item) for item in features]
    transition_output = transition_rows(window_output)
    strata_output = strata_rows(window_output, features)

    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        paths = {
            "candidates": stage / "candidates.csv",
            "windows": stage / "windows.csv",
            "transitions": stage / "transitions.csv",
            "strata": stage / "strata.csv",
        }
        write_rows(paths["candidates"], candidate_output, CANDIDATE_COLUMNS, "candidate")
        write_rows(paths["windows"], window_output, WINDOW_COLUMNS, "window")
        write_rows(
            paths["transitions"],
            transition_output,
            TRANSITION_COLUMNS,
            "transition",
        )
        write_rows(paths["strata"], strata_output, STRATA_COLUMNS, "stratum")
        write_json(
            stage / "index.json",
            output_index(
                interpretation_dir,
                interpretation_index,
                context_dir,
                context_index,
                paths,
                {
                    "candidates": len(candidate_output),
                    "windows": len(window_output),
                    "transitions": len(transition_output),
                    "strata": len(strata_output),
                },
            ),
        )
        sync_directory(stage)

        try:
            output_dir.mkdir()
        except FileExistsError as error:
            raise FileExistsError(
                "output directory appeared while phase error characterization was "
                f"running: {output_dir}"
            ) from error
        try:
            for name in (
                "candidates.csv",
                "windows.csv",
                "transitions.csv",
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


__all__ = [
    "CANDIDATE_COLUMNS",
    "STRATA_COLUMNS",
    "TRANSITION_COLUMNS",
    "WINDOW_COLUMNS",
    "build_features",
    "publish_phase_error_characterization",
]
