"""Exact recurrent-locus context for post-poly-C phase candidate windows."""

from __future__ import annotations

import csv
import math
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, TextIO

from .filesystem import file_sha256, sync_directory, validate_new_directory, write_json
from .model import PHASE_RECURRENT_LOCUS_SCHEMA_VERSION
from .phase_artifact import (
    CandidateRecord,
    WindowRecord,
    load_source as load_hypothesis_source,
    source_parameters,
    validate_source as validate_hypothesis_source,
)
from .phase_hypotheses import (
    PhaseObservation,
    PhaseWindow,
    candidate_contribution,
    load_after_observations,
    mass,
    mean,
    nonnegative_int,
    phase_windows,
    validate_source as validate_phase_source,
)

RECURRENT_POSITIONS = (253, 297, 302, 16194, 16197)

LOCUS_COLUMNS = (
    "validation_case_id",
    "read_sha256",
    "tract_id",
    "amplicon_id",
    "orientation",
    "interrupt_aligned_base",
    "position_1based",
    "read_order_distance_from_tract",
    "call_index_0based",
    "reference_base",
    "state",
    "aligned_base",
    "in_noisy_region",
    "profile_a",
    "profile_c",
    "profile_g",
    "profile_t",
    "profile_impurity",
    "reference_base_mass",
    "containing_windows",
)

WINDOW_COLUMNS = (
    "validation_case_id",
    "read_sha256",
    "tract_id",
    "amplicon_id",
    "orientation",
    "interrupt_aligned_base",
    "position_1based",
    "read_order_distance_from_tract",
    "window_id",
    "window_start_distance_after_tract",
    "window_end_distance_after_tract",
    "window_profile_observations",
    "window_noisy_observations",
    "window_mean_profile_impurity",
    "window_mean_zero_reference_mass",
    "locus_profile_impurity",
    "locus_reference_base_mass",
    "locus_in_noisy_region",
)

CANDIDATE_COLUMNS = (
    "validation_case_id",
    "read_sha256",
    "tract_id",
    "amplicon_id",
    "orientation",
    "interrupt_aligned_base",
    "position_1based",
    "read_order_distance_from_tract",
    "window_id",
    "reference_offset_in_read_order",
    "window_informative_positions",
    "window_mean_zero_reference_mass",
    "window_mean_shifted_reference_mass",
    "window_mean_residual_mass",
    "locus_informative_for_candidate",
    "locus_shifted_reference_base",
    "locus_zero_reference_mass",
    "locus_shifted_reference_mass",
    "locus_residual_mass",
)


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


def profile_values(
    observation: PhaseObservation,
) -> tuple[float | None, float | None, float | None, float | None]:
    if observation.profile is None:
        return None, None, None, None
    return observation.profile


def reference_mass(observation: PhaseObservation) -> float | None:
    if observation.profile is None:
        return None
    return mass(observation.profile, observation.reference_base)


def validate_generated_window(
    generated: PhaseWindow,
    source: WindowRecord,
) -> None:
    observations = generated.observations
    first = observations[0]
    last = observations[-1]
    if (
        source.validation_case_id != first.validation_case_id
        or source.read_sha256 != first.read_sha256
        or source.tract_id != first.tract_id
        or source.amplicon_id != (first.amplicon_id or "")
        or source.orientation != first.orientation
        or source.interrupt_aligned_base != (first.interrupt_aligned_base or "")
        or source.start_distance != first.distance
        or source.end_distance != last.distance
        or source.profile_observations != len(observations)
    ):
        raise ValueError(f"{generated.window_id}: reconstructed window metadata differs")

    noisy = sum(observation.in_noisy_region is True for observation in observations)
    if source.noisy_observations != noisy:
        raise ValueError(f"{generated.window_id}: reconstructed noisy count differs")

    impurities = [
        observation.profile_impurity
        for observation in observations
        if observation.profile_impurity is not None
    ]
    zero_masses = [
        mass(observation.profile, observation.reference_base)
        for observation in observations
        if observation.profile is not None
    ]
    if len(impurities) != len(observations) or len(zero_masses) != len(observations):
        raise ValueError(f"{generated.window_id}: reconstructed window lacks profile data")
    if abs(source.mean_profile_impurity - mean(impurities)) > 1e-9:
        raise ValueError(f"{generated.window_id}: reconstructed impurity differs")
    if abs(source.mean_zero_reference_mass - mean(zero_masses)) > 1e-9:
        raise ValueError(f"{generated.window_id}: reconstructed zero mass differs")


def reconstruct_windows(
    groups: dict[tuple[str, str], list[PhaseObservation]],
    source_windows: dict[str, WindowRecord],
    window_size: int,
    window_step: int,
) -> list[PhaseWindow]:
    generated = phase_windows(groups, window_size, window_step)
    generated_ids = {window.window_id for window in generated}
    source_ids = set(source_windows)
    if generated_ids != source_ids:
        missing = sorted(source_ids - generated_ids)
        extra = sorted(generated_ids - source_ids)
        raise ValueError(
            "reconstructed phase windows differ from source hypotheses: "
            f"missing={missing[:3]} extra={extra[:3]}"
        )
    for window in generated:
        validate_generated_window(window, source_windows[window.window_id])
    return generated


def membership_map(
    windows: list[PhaseWindow],
) -> dict[tuple[str, str, int], list[str]]:
    memberships: dict[tuple[str, str, int], list[str]] = {}
    for window in windows:
        for observation in window.observations:
            key = (
                observation.read_sha256,
                observation.tract_id,
                observation.distance,
            )
            memberships.setdefault(key, []).append(window.window_id)
    for window_ids in memberships.values():
        window_ids.sort()
    return memberships


def target_observations(
    groups: dict[tuple[str, str], list[PhaseObservation]],
) -> list[PhaseObservation]:
    targets = [
        observation
        for rows in groups.values()
        for observation in rows
        if observation.position_1based in RECURRENT_POSITIONS
    ]
    return sorted(
        targets,
        key=lambda observation: (
            observation.position_1based,
            observation.validation_case_id,
            observation.read_sha256,
            observation.tract_id,
            observation.distance,
        ),
    )


def locus_row(
    observation: PhaseObservation,
    containing_windows: list[str],
) -> dict[str, Any]:
    profile_a, profile_c, profile_g, profile_t = profile_values(observation)
    return {
        "validation_case_id": observation.validation_case_id,
        "read_sha256": observation.read_sha256,
        "tract_id": observation.tract_id,
        "amplicon_id": observation.amplicon_id,
        "orientation": observation.orientation,
        "interrupt_aligned_base": observation.interrupt_aligned_base,
        "position_1based": observation.position_1based,
        "read_order_distance_from_tract": observation.distance,
        "call_index_0based": observation.call_index,
        "reference_base": observation.reference_base,
        "state": observation.state,
        "aligned_base": observation.aligned_base,
        "in_noisy_region": observation.in_noisy_region,
        "profile_a": profile_a,
        "profile_c": profile_c,
        "profile_g": profile_g,
        "profile_t": profile_t,
        "profile_impurity": observation.profile_impurity,
        "reference_base_mass": reference_mass(observation),
        "containing_windows": len(containing_windows),
    }


def window_context_row(
    observation: PhaseObservation,
    source: WindowRecord,
) -> dict[str, Any]:
    return {
        "validation_case_id": observation.validation_case_id,
        "read_sha256": observation.read_sha256,
        "tract_id": observation.tract_id,
        "amplicon_id": observation.amplicon_id,
        "orientation": observation.orientation,
        "interrupt_aligned_base": observation.interrupt_aligned_base,
        "position_1based": observation.position_1based,
        "read_order_distance_from_tract": observation.distance,
        "window_id": source.window_id,
        "window_start_distance_after_tract": source.start_distance,
        "window_end_distance_after_tract": source.end_distance,
        "window_profile_observations": source.profile_observations,
        "window_noisy_observations": source.noisy_observations,
        "window_mean_profile_impurity": source.mean_profile_impurity,
        "window_mean_zero_reference_mass": source.mean_zero_reference_mass,
        "locus_profile_impurity": observation.profile_impurity,
        "locus_reference_base_mass": reference_mass(observation),
        "locus_in_noisy_region": observation.in_noisy_region,
    }


def candidate_context_row(
    observation: PhaseObservation,
    window_id: str,
    candidate: CandidateRecord,
    reference_by_distance: dict[int, str],
) -> dict[str, Any]:
    contribution = candidate_contribution(
        observation,
        reference_by_distance,
        candidate.offset,
    )
    if contribution is not None and candidate.informative_positions == 0:
        raise ValueError(
            f"{window_id}:{candidate.offset}: locus informative but window candidate is not"
        )
    return {
        "validation_case_id": observation.validation_case_id,
        "read_sha256": observation.read_sha256,
        "tract_id": observation.tract_id,
        "amplicon_id": observation.amplicon_id,
        "orientation": observation.orientation,
        "interrupt_aligned_base": observation.interrupt_aligned_base,
        "position_1based": observation.position_1based,
        "read_order_distance_from_tract": observation.distance,
        "window_id": window_id,
        "reference_offset_in_read_order": candidate.offset,
        "window_informative_positions": candidate.informative_positions,
        "window_mean_zero_reference_mass": candidate.zero_mass,
        "window_mean_shifted_reference_mass": candidate.shifted_mass,
        "window_mean_residual_mass": candidate.residual_mass,
        "locus_informative_for_candidate": contribution is not None,
        "locus_shifted_reference_base": (
            contribution.shifted_base if contribution is not None else None
        ),
        "locus_zero_reference_mass": (
            contribution.zero_mass if contribution is not None else None
        ),
        "locus_shifted_reference_mass": (
            contribution.shifted_mass if contribution is not None else None
        ),
        "locus_residual_mass": (
            contribution.residual_mass if contribution is not None else None
        ),
    }


def build_rows(
    groups: dict[tuple[str, str], list[PhaseObservation]],
    generated_windows: list[PhaseWindow],
    source_windows: dict[str, WindowRecord],
    candidates: dict[tuple[str, int], CandidateRecord],
    offsets: tuple[int, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    memberships = membership_map(generated_windows)
    references = {
        key: {observation.distance: observation.reference_base for observation in rows}
        for key, rows in groups.items()
    }
    loci: list[dict[str, Any]] = []
    windows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []

    for observation in target_observations(groups):
        key = (
            observation.read_sha256,
            observation.tract_id,
            observation.distance,
        )
        containing = memberships.get(key, [])
        loci.append(locus_row(observation, containing))
        references_for_read = references[
            (observation.read_sha256, observation.tract_id)
        ]
        for window_id in containing:
            windows.append(window_context_row(observation, source_windows[window_id]))
            for offset in offsets:
                candidate_rows.append(
                    candidate_context_row(
                        observation,
                        window_id,
                        candidates[(window_id, offset)],
                        references_for_read,
                    )
                )

    return loci, windows, candidate_rows


def output_index(
    phase_dir: Path,
    hypotheses_dir: Path,
    phase_index: dict[str, Any],
    hypothesis_index: dict[str, Any],
    offsets: tuple[int, ...],
    loci_path: Path,
    windows_path: Path,
    candidates_path: Path,
    loci_rows: int,
    window_rows: int,
    candidate_rows: int,
) -> dict[str, Any]:
    return {
        "schema_version": PHASE_RECURRENT_LOCUS_SCHEMA_VERSION,
        "source_polyc_phase_sha256": file_sha256(phase_dir / "index.json"),
        "source_phase_hypotheses_sha256": file_sha256(
            hypotheses_dir / "index.json"
        ),
        "source_corpus_sha256": phase_index["source_corpus_sha256"],
        "signal_version": phase_index["signal_version"],
        "manifest_sha256": phase_index["manifest_sha256"],
        "reference_sha256": phase_index["reference_sha256"],
        "configuration_sha256": phase_index["configuration_sha256"],
        "method": {
            "recurrent_positions_1based": list(RECURRENT_POSITIONS),
            "source_window_size_profile_observations": hypothesis_index["method"][
                "window_size_profile_observations"
            ],
            "source_window_step_profile_observations": hypothesis_index["method"][
                "window_step_profile_observations"
            ],
            "candidate_offsets": list(offsets),
            "window_membership": (
                "exact membership reconstructed from consecutive profile-bearing "
                "post-tract observations using the authoritative phase window generator"
            ),
            "candidate_context": (
                "complete source candidate curve plus exact recurrent-locus contribution "
                "for each containing window and offset"
            ),
            "candidate_selection": "none; every source offset retained",
            "thresholds": "none",
        },
        "loci_file": "loci.csv",
        "loci_sha256": file_sha256(loci_path),
        "loci_rows": loci_rows,
        "loci_columns": list(LOCUS_COLUMNS),
        "windows_file": "windows.csv",
        "windows_sha256": file_sha256(windows_path),
        "windows_rows": window_rows,
        "windows_columns": list(WINDOW_COLUMNS),
        "candidates_file": "candidates.csv",
        "candidates_sha256": file_sha256(candidates_path),
        "candidates_rows": candidate_rows,
        "candidates_columns": list(CANDIDATE_COLUMNS),
    }


def validate_source_pair(
    phase_dir: Path,
    hypotheses_dir: Path,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    tuple[int, ...],
    dict[tuple[str, str], list[PhaseObservation]],
    dict[str, WindowRecord],
    dict[tuple[str, int], CandidateRecord],
    list[PhaseWindow],
]:
    phase_index = validate_phase_source(phase_dir)
    hypothesis_index, offsets = validate_hypothesis_source(hypotheses_dir)
    phase_sha256 = file_sha256(phase_dir / "index.json")
    if hypothesis_index["source_polyc_phase_sha256"] != phase_sha256:
        raise ValueError("phase-hypothesis source poly-C phase SHA-256 mismatch")

    for key in (
        "source_corpus_sha256",
        "signal_version",
        "manifest_sha256",
        "reference_sha256",
        "configuration_sha256",
    ):
        if hypothesis_index[key] != phase_index[key]:
            raise ValueError(f"phase/hypothesis provenance differs for {key}")

    parameters = source_parameters(hypothesis_index["method"])
    groups = load_after_observations(
        phase_dir,
        nonnegative_int(phase_index["observations_rows"], "observations_rows"),
    )
    source_windows, candidates = load_hypothesis_source(
        hypotheses_dir,
        hypothesis_index,
        offsets,
    )
    generated_windows = reconstruct_windows(
        groups,
        source_windows,
        parameters.window_size,
        parameters.window_step,
    )
    return (
        phase_index,
        hypothesis_index,
        offsets,
        groups,
        source_windows,
        candidates,
        generated_windows,
    )


def publish_phase_recurrent_loci(
    phase_dir: Path,
    hypotheses_dir: Path,
    output_dir: Path,
) -> None:
    phase_dir = phase_dir.resolve()
    hypotheses_dir = hypotheses_dir.resolve()
    output_dir = output_dir.resolve()
    if not phase_dir.is_dir():
        raise ValueError(f"poly-C phase directory does not exist: {phase_dir}")
    if not hypotheses_dir.is_dir():
        raise ValueError(
            f"phase-hypothesis directory does not exist: {hypotheses_dir}"
        )
    validate_new_directory(output_dir, (phase_dir, hypotheses_dir))
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if not output_dir.parent.is_dir() or output_dir.parent.is_symlink():
        raise ValueError(
            f"output parent is not a regular directory: {output_dir.parent}"
        )

    (
        phase_index,
        hypothesis_index,
        offsets,
        groups,
        source_windows,
        candidates,
        generated_windows,
    ) = validate_source_pair(phase_dir, hypotheses_dir)
    loci, windows, candidate_rows = build_rows(
        groups,
        generated_windows,
        source_windows,
        candidates,
        offsets,
    )

    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        loci_path = stage / "loci.csv"
        windows_path = stage / "windows.csv"
        candidates_path = stage / "candidates.csv"
        write_rows(loci_path, loci, LOCUS_COLUMNS, "recurrent locus")
        write_rows(windows_path, windows, WINDOW_COLUMNS, "recurrent window")
        write_rows(
            candidates_path,
            candidate_rows,
            CANDIDATE_COLUMNS,
            "recurrent candidate",
        )
        write_json(
            stage / "index.json",
            output_index(
                phase_dir,
                hypotheses_dir,
                phase_index,
                hypothesis_index,
                offsets,
                loci_path,
                windows_path,
                candidates_path,
                len(loci),
                len(windows),
                len(candidate_rows),
            ),
        )
        sync_directory(stage)

        try:
            output_dir.mkdir()
        except FileExistsError as error:
            raise FileExistsError(
                "output directory appeared while recurrent-locus research was running: "
                f"{output_dir}"
            ) from error
        try:
            for name in ("loci.csv", "windows.csv", "candidates.csv", "index.json"):
                os.rename(stage / name, output_dir / name)
            sync_directory(output_dir)
            sync_directory(output_dir.parent)
        except OSError:
            shutil.rmtree(output_dir, ignore_errors=True)
            sync_directory(output_dir.parent)
            raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
