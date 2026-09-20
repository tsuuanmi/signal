"""Windowed candidate phase hypotheses for post-poly-C validation research."""

from __future__ import annotations

import csv
import json
import math
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from .filesystem import file_sha256, sync_directory, validate_new_directory, write_json
from .model import PHASE_HYPOTHESIS_SCHEMA_VERSION, POLYC_PHASE_SCHEMA_VERSION
from .polyc_phase import OBSERVATION_COLUMNS, SUMMARY_COLUMNS
from .research_loader import strict_keys

SOURCE_INDEX_FIELDS = (
    "schema_version",
    "source_corpus_sha256",
    "signal_version",
    "manifest_sha256",
    "reference_sha256",
    "configuration_sha256",
    "method",
    "crossing_reads",
    "observations_file",
    "observations_sha256",
    "observations_rows",
    "observations_columns",
    "summary_file",
    "summary_sha256",
    "summary_rows",
    "summary_columns",
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
    "start_call_index_0based",
    "end_call_index_0based",
    "profile_observations",
    "noisy_observations",
    "mean_profile_impurity",
    "mean_zero_reference_mass",
)

HYPOTHESIS_COLUMNS = (
    "window_id",
    "reference_offset_in_read_order",
    "informative_positions",
    "mean_zero_reference_mass",
    "mean_shifted_reference_mass",
    "mean_residual_mass",
)


@dataclass(frozen=True)
class PhaseObservation:
    validation_case_id: str
    read_sha256: str
    tract_id: str
    amplicon_id: str | None
    orientation: str
    interrupt_aligned_base: str | None
    distance: int
    call_index: int | None
    reference_base: str
    in_noisy_region: bool | None
    profile: tuple[float, float, float, float] | None
    profile_impurity: float | None


def json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}: invalid JSON: {error.msg}") from error
    if not isinstance(value, dict):
        raise TypeError(f"{path}: expected a JSON object")
    return value


def nonnegative_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def optional_nonnegative_int(value: str, label: str) -> int | None:
    if value == "":
        return None
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{label} must be an integer or empty") from error
    if parsed < 0:
        raise ValueError(f"{label} must be non-negative")
    return parsed


def positive_int(value: str, label: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{label} must be an integer") from error
    if parsed <= 0:
        raise ValueError(f"{label} must be positive")
    return parsed


def optional_boolean(value: str, label: str) -> bool | None:
    if value == "":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"{label} must be true, false, or empty")


def optional_base(value: str, label: str) -> str | None:
    if value == "":
        return None
    if value not in {"A", "C", "G", "T"}:
        raise ValueError(f"{label} must be A/C/G/T or empty")
    return value


def profile(
    row: dict[str, str], label: str
) -> tuple[float, float, float, float] | None:
    raw = tuple(row[f"profile_{base}"] for base in ("a", "c", "g", "t"))
    if all(value == "" for value in raw):
        return None
    if any(value == "" for value in raw):
        raise ValueError(f"{label}: profile channels must be all present or all absent")
    try:
        values = tuple(float(value) for value in raw)
    except ValueError as error:
        raise ValueError(f"{label}: profile channels must be numeric") from error
    if any(not math.isfinite(value) or value < 0.0 or value > 1.0 for value in values):
        raise ValueError(f"{label}: profile channels must be finite in [0, 1]")
    if abs(sum(values) - 1.0) > 1e-9:
        raise ValueError(f"{label}: profile channels must sum to one")
    return values[0], values[1], values[2], values[3]


def mass(values: tuple[float, float, float, float], base: str) -> float:
    return values[{"A": 0, "C": 1, "G": 2, "T": 3}[base]]


def validate_source(phase_dir: Path) -> dict[str, Any]:
    index_path = phase_dir / "index.json"
    if not index_path.is_file():
        raise ValueError(f"poly-C phase index is not a regular file: {index_path}")
    index = json_object(index_path)
    strict_keys(index, SOURCE_INDEX_FIELDS, "poly-C phase index")
    if index["schema_version"] != POLYC_PHASE_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported poly-C phase schema: {index['schema_version']!r}"
        )

    specs = (
        (
            "observations.csv",
            OBSERVATION_COLUMNS,
            "observations_file",
            "observations_sha256",
            "observations_rows",
            "observations_columns",
        ),
        (
            "summary.csv",
            SUMMARY_COLUMNS,
            "summary_file",
            "summary_sha256",
            "summary_rows",
            "summary_columns",
        ),
    )
    for filename, columns, file_key, sha_key, rows_key, columns_key in specs:
        if index[file_key] != filename:
            raise ValueError(f"poly-C phase {file_key} must be {filename}")
        if index[columns_key] != list(columns):
            raise ValueError(f"poly-C phase {columns_key} differ from current contract")
        path = phase_dir / filename
        if not path.is_file():
            raise ValueError(f"poly-C phase table is not a regular file: {path}")
        if index[sha_key] != file_sha256(path):
            raise ValueError(f"{filename} SHA-256 mismatch")
        nonnegative_int(index[rows_key], f"poly-C phase {rows_key}")
    return index


def parse_observation(row: dict[str, str], line: int) -> PhaseObservation | None:
    label = f"observations.csv:{line}"
    if row["path_region"] != "after":
        return None

    distance = positive_int(
        row["read_order_distance_from_tract"],
        f"{label}.read_order_distance_from_tract",
    )
    values = profile(row, label)
    impurity = None
    if values is not None:
        try:
            impurity = float(row["profile_impurity"])
        except ValueError as error:
            raise ValueError(f"{label}.profile_impurity must be numeric") from error
        expected = 1.0 - max(values)
        if not math.isfinite(impurity) or abs(impurity - expected) > 1e-9:
            raise ValueError(f"{label}.profile_impurity does not match profile")
    elif row["profile_impurity"] != "":
        raise ValueError(f"{label}.profile_impurity requires a profile")

    reference_base = row["reference_base"]
    if reference_base not in {"A", "C", "G", "T"}:
        raise ValueError(f"{label}.reference_base must be A/C/G/T")
    orientation = row["orientation"]
    if orientation not in {"forward", "reverse"}:
        raise ValueError(f"{label}.orientation must be forward or reverse")

    validation_case_id = row["validation_case_id"]
    read_sha256 = row["read_sha256"]
    tract_id = row["tract_id"]
    if not validation_case_id or not read_sha256 or not tract_id:
        raise ValueError(f"{label}: missing case/read/tract identity")

    return PhaseObservation(
        validation_case_id=validation_case_id,
        read_sha256=read_sha256,
        tract_id=tract_id,
        amplicon_id=row["amplicon_id"] or None,
        orientation=orientation,
        interrupt_aligned_base=optional_base(
            row["interrupt_aligned_base"],
            f"{label}.interrupt_aligned_base",
        ),
        distance=distance,
        call_index=optional_nonnegative_int(
            row["call_index_0based"],
            f"{label}.call_index_0based",
        ),
        reference_base=reference_base,
        in_noisy_region=optional_boolean(
            row["in_noisy_region"],
            f"{label}.in_noisy_region",
        ),
        profile=values,
        profile_impurity=impurity,
    )


def load_after_observations(
    phase_dir: Path,
    expected_rows: int,
) -> dict[tuple[str, str], list[PhaseObservation]]:
    path = phase_dir / "observations.csv"
    groups: dict[tuple[str, str], list[PhaseObservation]] = {}
    rows_seen = 0
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or tuple(reader.fieldnames) != OBSERVATION_COLUMNS:
            raise ValueError(f"{path}: unexpected columns")
        for line, row in enumerate(reader, 2):
            rows_seen += 1
            parsed = parse_observation(row, line)
            if parsed is not None:
                groups.setdefault((parsed.read_sha256, parsed.tract_id), []).append(
                    parsed
                )
    if rows_seen != expected_rows:
        raise ValueError(f"{path}: expected {expected_rows} rows, found {rows_seen}")

    for key, rows in groups.items():
        distances = [row.distance for row in rows]
        if len(distances) != len(set(distances)):
            raise ValueError(f"{key}: duplicate post-tract reference distance")
        first = rows[0]
        for row in rows[1:]:
            if (
                row.validation_case_id != first.validation_case_id
                or row.amplicon_id != first.amplicon_id
                or row.orientation != first.orientation
                or row.interrupt_aligned_base != first.interrupt_aligned_base
            ):
                raise ValueError(
                    f"{key}: read/tract metadata changes across observations"
                )
        rows.sort(key=lambda row: row.distance)
    return groups


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    return value


def csv_writer(target: TextIO, columns: tuple[str, ...]) -> csv.DictWriter:
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


def candidate_metrics(
    window: list[PhaseObservation],
    reference_by_distance: dict[int, str],
    offset: int,
) -> tuple[int, float | None, float | None, float | None]:
    zero_masses: list[float] = []
    shifted_masses: list[float] = []
    residual_masses: list[float] = []

    for observation in window:
        if observation.profile is None:
            continue
        shifted_base = reference_by_distance.get(observation.distance + offset)
        if shifted_base is None or shifted_base == observation.reference_base:
            continue
        zero_mass = mass(observation.profile, observation.reference_base)
        shifted_mass = mass(observation.profile, shifted_base)
        residual = 1.0 - zero_mass - shifted_mass
        if residual < -1e-9:
            raise ValueError("candidate phase mass exceeds normalized profile mass")
        zero_masses.append(zero_mass)
        shifted_masses.append(shifted_mass)
        residual_masses.append(max(0.0, residual))

    if not zero_masses:
        return 0, None, None, None
    return (
        len(zero_masses),
        mean(zero_masses),
        mean(shifted_masses),
        mean(residual_masses),
    )


def window_rows(
    groups: dict[tuple[str, str], list[PhaseObservation]],
    window_size: int,
    window_step: int,
    max_offset: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    windows: list[dict[str, Any]] = []
    hypotheses: list[dict[str, Any]] = []
    offsets = tuple(range(-max_offset, 0)) + tuple(range(1, max_offset + 1))

    for key in sorted(groups):
        rows = groups[key]
        reference_by_distance = {row.distance: row.reference_base for row in rows}
        profiled = [row for row in rows if row.profile is not None]
        if len(profiled) < window_size:
            continue

        for start in range(0, len(profiled) - window_size + 1, window_step):
            window = profiled[start : start + window_size]
            first = window[0]
            last = window[-1]
            window_id = (
                f"{first.tract_id}:{first.read_sha256}:{first.distance}-{last.distance}"
            )
            zero_masses = [
                mass(row.profile, row.reference_base)
                for row in window
                if row.profile is not None
            ]
            impurities = [
                row.profile_impurity
                for row in window
                if row.profile_impurity is not None
            ]
            windows.append(
                {
                    "window_id": window_id,
                    "validation_case_id": first.validation_case_id,
                    "read_sha256": first.read_sha256,
                    "tract_id": first.tract_id,
                    "amplicon_id": first.amplicon_id,
                    "orientation": first.orientation,
                    "interrupt_aligned_base": first.interrupt_aligned_base,
                    "start_distance_after_tract": first.distance,
                    "end_distance_after_tract": last.distance,
                    "start_call_index_0based": first.call_index,
                    "end_call_index_0based": last.call_index,
                    "profile_observations": len(window),
                    "noisy_observations": sum(
                        row.in_noisy_region is True for row in window
                    ),
                    "mean_profile_impurity": mean(impurities),
                    "mean_zero_reference_mass": mean(zero_masses),
                }
            )

            for offset in offsets:
                informative, zero_mass, shifted_mass, residual_mass = candidate_metrics(
                    window,
                    reference_by_distance,
                    offset,
                )
                hypotheses.append(
                    {
                        "window_id": window_id,
                        "reference_offset_in_read_order": offset,
                        "informative_positions": informative,
                        "mean_zero_reference_mass": zero_mass,
                        "mean_shifted_reference_mass": shifted_mass,
                        "mean_residual_mass": residual_mass,
                    }
                )

    if not windows:
        raise ValueError(
            "poly-C phase artifact contains no complete post-tract windows"
        )
    return windows, hypotheses


def output_index(
    phase_dir: Path,
    source_index: dict[str, Any],
    windows_path: Path,
    hypotheses_path: Path,
    windows: list[dict[str, Any]],
    hypotheses: list[dict[str, Any]],
    window_size: int,
    window_step: int,
    max_offset: int,
) -> dict[str, Any]:
    return {
        "schema_version": PHASE_HYPOTHESIS_SCHEMA_VERSION,
        "source_polyc_phase_sha256": file_sha256(phase_dir / "index.json"),
        "source_corpus_sha256": source_index["source_corpus_sha256"],
        "signal_version": source_index["signal_version"],
        "manifest_sha256": source_index["manifest_sha256"],
        "reference_sha256": source_index["reference_sha256"],
        "configuration_sha256": source_index["configuration_sha256"],
        "method": {
            "window_size_profile_observations": window_size,
            "window_step_profile_observations": window_step,
            "max_reference_offset_in_read_order": max_offset,
            "candidate_offsets": [
                *range(-max_offset, 0),
                *range(1, max_offset + 1),
            ],
            "informative_position_rule": (
                "unshifted and candidate-shifted reference bases differ"
            ),
            "candidate_evidence": (
                "mean normalized profile mass on unshifted base, shifted base, "
                "and all remaining bases"
            ),
            "candidate_selection": "none; complete candidate curve retained",
        },
        "windows_file": "windows.csv",
        "windows_sha256": file_sha256(windows_path),
        "windows_rows": len(windows),
        "windows_columns": list(WINDOW_COLUMNS),
        "hypotheses_file": "hypotheses.csv",
        "hypotheses_sha256": file_sha256(hypotheses_path),
        "hypotheses_rows": len(hypotheses),
        "hypotheses_columns": list(HYPOTHESIS_COLUMNS),
    }


def publish_phase_hypotheses(
    phase_dir: Path,
    output_dir: Path,
    *,
    window_size: int = 25,
    window_step: int = 5,
    max_offset: int = 5,
) -> None:
    phase_dir = phase_dir.resolve()
    output_dir = output_dir.resolve()
    if not phase_dir.is_dir():
        raise ValueError(f"poly-C phase directory does not exist: {phase_dir}")
    if window_size <= 0 or window_step <= 0 or max_offset <= 0:
        raise ValueError("window size, window step, and max offset must be positive")
    validate_new_directory(output_dir, (phase_dir,))
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if not output_dir.parent.is_dir() or output_dir.parent.is_symlink():
        raise ValueError(
            f"output parent is not a regular directory: {output_dir.parent}"
        )

    source_index = validate_source(phase_dir)
    groups = load_after_observations(
        phase_dir,
        nonnegative_int(source_index["observations_rows"], "observations_rows"),
    )
    windows, hypotheses = window_rows(
        groups,
        window_size,
        window_step,
        max_offset,
    )

    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        windows_path = stage / "windows.csv"
        with windows_path.open("x", encoding="utf-8", newline="") as target:
            built = csv_writer(target, WINDOW_COLUMNS)
            for index, row in enumerate(windows):
                write_row(built, row, WINDOW_COLUMNS, f"window row {index}")
            target.flush()
            os.fsync(target.fileno())

        hypotheses_path = stage / "hypotheses.csv"
        with hypotheses_path.open("x", encoding="utf-8", newline="") as target:
            built = csv_writer(target, HYPOTHESIS_COLUMNS)
            for index, row in enumerate(hypotheses):
                write_row(built, row, HYPOTHESIS_COLUMNS, f"hypothesis row {index}")
            target.flush()
            os.fsync(target.fileno())

        write_json(
            stage / "index.json",
            output_index(
                phase_dir,
                source_index,
                windows_path,
                hypotheses_path,
                windows,
                hypotheses,
                window_size,
                window_step,
                max_offset,
            ),
        )
        sync_directory(stage)

        try:
            output_dir.mkdir()
        except FileExistsError as error:
            raise FileExistsError(
                f"output directory appeared while phase hypotheses were running: "
                f"{output_dir}"
            ) from error
        try:
            for name in ("windows.csv", "hypotheses.csv", "index.json"):
                os.rename(stage / name, output_dir / name)
            sync_directory(output_dir)
            sync_directory(output_dir.parent)
        except OSError:
            shutil.rmtree(output_dir, ignore_errors=True)
            sync_directory(output_dir.parent)
            raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
