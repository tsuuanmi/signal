"""Descriptive mtDNA poly-C phase-instability research from validation measurements."""

from __future__ import annotations

import csv
import math
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO

from .filesystem import file_sha256, sync_directory, validate_new_directory, write_json
from .model import POLYC_PHASE_SCHEMA_VERSION
from .research_loader import iter_research_rows, load_research_corpus
from .research_model import ResearchCorpus
from .research_statistics import nearest_rank

OBSERVATION_COLUMNS = (
    "validation_case_id",
    "source_group_id",
    "specimen_group_id",
    "read_sha256",
    "amplicon_id",
    "declared_direction",
    "orientation",
    "tract_id",
    "tract_start_1based",
    "tract_end_1based",
    "interrupt_position_1based",
    "position_1based",
    "path_region",
    "read_order_distance_from_tract",
    "call_index_0based",
    "call_distance_from_tract",
    "reference_base",
    "state",
    "aligned_base",
    "quality",
    "in_noisy_region",
    "profile_a",
    "profile_c",
    "profile_g",
    "profile_t",
    "profile_impurity",
    "read_order_previous_reference_base",
    "previous_reference_base_mass",
    "reference_base_mass",
    "read_order_next_reference_base",
    "next_reference_base_mass",
    "interrupt_state",
    "interrupt_aligned_base",
    "interrupt_call_index_0based",
    "interrupt_profile_a",
    "interrupt_profile_c",
    "interrupt_profile_g",
    "interrupt_profile_t",
    "interrupt_in_noisy_region",
)

SUMMARY_COLUMNS = (
    "tract_id",
    "amplicon_id",
    "orientation",
    "interrupt_aligned_base",
    "path_region",
    "observations",
    "profile_observations",
    "noisy_observations",
    "mean_profile_impurity",
    "p50_profile_impurity",
    "p90_profile_impurity",
    "mean_previous_reference_base_mass",
    "p50_previous_reference_base_mass",
    "p90_previous_reference_base_mass",
    "mean_next_reference_base_mass",
    "p50_next_reference_base_mass",
    "p90_next_reference_base_mass",
)


@dataclass(frozen=True)
class PolyCTract:
    tract_id: str
    start_1based: int
    end_1based: int
    interrupt_position_1based: int
    reference_sequence: str


TRACTS = (
    PolyCTract("HV2_C", 303, 315, 310, "CCCCCCCTCCCCC"),
    PolyCTract("HV1_C", 16184, 16193, 16189, "CCCCCTCCCC"),
)


@dataclass
class ReadContext:
    validation_case_id: str
    source_group_id: str
    specimen_group_id: str | None
    read_sha256: str
    amplicon_id: str | None
    declared_direction: str | None
    orientation: str
    tract_positions: set[int] = field(default_factory=set)
    special_observations: dict[int, dict[str, Any]] = field(default_factory=dict)


@dataclass
class SummaryAccumulator:
    observations: int = 0
    noisy_observations: int = 0
    impurities: list[float] = field(default_factory=list)
    previous_masses: list[float] = field(default_factory=list)
    next_masses: list[float] = field(default_factory=list)

    def add(self, row: dict[str, Any]) -> None:
        self.observations += 1
        if row["in_noisy_region"] is True:
            self.noisy_observations += 1
        for key, target in (
            ("profile_impurity", self.impurities),
            ("previous_reference_base_mass", self.previous_masses),
            ("next_reference_base_mass", self.next_masses),
        ):
            value = row[key]
            if value is not None:
                target.append(float(value))


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


def write_row(
    target: csv.DictWriter,
    row: dict[str, Any],
    columns: tuple[str, ...],
    label: str,
) -> None:
    expected = set(columns)
    if set(row) != expected:
        missing = sorted(expected - set(row))
        extra = sorted(set(row) - expected)
        raise ValueError(
            f"{label} does not match table columns: missing={missing} extra={extra}"
        )
    target.writerow({key: csv_value(row[key]) for key in columns})


def orientation(value: Any, label: str) -> str:
    if value not in {"forward", "reverse"}:
        raise ValueError(f"{label} must be forward or reverse")
    return str(value)


def profile(row: dict[str, Any]) -> tuple[float, float, float, float] | None:
    values = tuple(row[f"profile_{base}"] for base in ("a", "c", "g", "t"))
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise ValueError("profile channels must be all present or all absent")
    converted = tuple(float(value) for value in values)
    if any(not math.isfinite(value) or value < 0.0 for value in converted):
        raise ValueError("profile channels must be finite and non-negative")
    if abs(sum(converted) - 1.0) > 1e-9:
        raise ValueError("profile channels must sum to one")
    return converted[0], converted[1], converted[2], converted[3]


def mass_for_base(values: tuple[float, float, float, float], base: str) -> float:
    try:
        index = {"A": 0, "C": 1, "G": 2, "T": 3}[base]
    except KeyError as error:
        raise ValueError(f"unsupported reference base {base!r}") from error
    return values[index]


def path_region(tract: PolyCTract, selected_orientation: str, position: int) -> str:
    if tract.start_1based <= position <= tract.end_1based:
        return "inside"
    if selected_orientation == "forward":
        return "before" if position < tract.start_1based else "after"
    return "before" if position > tract.end_1based else "after"


def read_order_distance(
    tract: PolyCTract,
    selected_orientation: str,
    position: int,
) -> int:
    region = path_region(tract, selected_orientation, position)
    if region == "inside":
        return 0
    if selected_orientation == "forward":
        return (
            position - tract.end_1based
            if region == "after"
            else position - tract.start_1based
        )
    return (
        tract.start_1based - position
        if region == "after"
        else tract.end_1based - position
    )


def reference_neighbor_positions(
    selected_orientation: str,
    position: int,
) -> tuple[int, int]:
    if selected_orientation == "forward":
        return position - 1, position + 1
    return position + 1, position - 1


def tract_call_boundary(
    context: ReadContext,
    tract: PolyCTract,
    region: str,
) -> int | None:
    if region == "inside":
        return None
    if context.orientation == "forward":
        boundary = tract.start_1based if region == "before" else tract.end_1based
    else:
        boundary = tract.end_1based if region == "before" else tract.start_1based
    observation = context.special_observations.get(boundary)
    if observation is None:
        return None
    call_index = observation["call_index_0based"]
    return int(call_index) if call_index is not None else None


def call_distance(
    context: ReadContext,
    tract: PolyCTract,
    row: dict[str, Any],
    region: str,
) -> int | None:
    if region == "inside":
        return 0
    call_index = row["call_index_0based"]
    boundary = tract_call_boundary(context, tract, region)
    if call_index is None or boundary is None:
        return None
    distance = int(call_index) - boundary
    if region == "after" and distance <= 0:
        raise ValueError(
            f"{context.read_sha256}: after-tract call distance must be positive"
        )
    if region == "before" and distance >= 0:
        raise ValueError(
            f"{context.read_sha256}: before-tract call distance must be negative"
        )
    return distance


def read_crosses_tract(context: ReadContext, tract: PolyCTract) -> bool:
    return all(
        position in context.tract_positions
        for position in range(tract.start_1based, tract.end_1based + 1)
    )


def validate_reference_tracts(
    reference_bases: dict[int, str],
) -> tuple[PolyCTract, ...]:
    active: list[PolyCTract] = []
    for tract in TRACTS:
        positions = range(tract.start_1based, tract.end_1based + 1)
        present = [position in reference_bases for position in positions]
        if not any(present):
            continue
        if not all(present):
            raise ValueError(
                f"{tract.tract_id}: validation corpus only partially represents "
                "the rCRS poly-C tract"
            )
        sequence = "".join(reference_bases[position] for position in positions)
        if sequence != tract.reference_sequence:
            raise ValueError(
                f"{tract.tract_id}: reference sequence {sequence!r} differs from "
                f"expected rCRS tract {tract.reference_sequence!r}"
            )
        active.append(tract)
    if not active:
        raise ValueError(
            "validation corpus contains no complete supported rCRS poly-C tract"
        )
    return tuple(active)


def scan_context(
    corpus: ResearchCorpus,
) -> tuple[dict[str, ReadContext], dict[int, str], tuple[PolyCTract, ...]]:
    contexts: dict[str, ReadContext] = {}
    reference_bases: dict[int, str] = {}
    tract_positions = {
        position
        for tract in TRACTS
        for position in range(tract.start_1based, tract.end_1based + 1)
    }
    special_positions = {
        position
        for tract in TRACTS
        for position in (
            tract.start_1based,
            tract.end_1based,
            tract.interrupt_position_1based,
        )
    }

    for locus_row, observation_rows in iter_research_rows(corpus):
        position = int(locus_row["position_1based"])
        reference_base = str(locus_row["reference_base"])
        previous = reference_bases.setdefault(position, reference_base)
        if previous != reference_base:
            raise ValueError(
                f"reference base at position {position} changes across validation cases"
            )

        for row in observation_rows:
            read_sha256 = str(row["read_sha256"])
            selected_orientation = orientation(
                row["orientation"],
                f"{read_sha256}.orientation",
            )
            context = contexts.get(read_sha256)
            if context is None:
                context = ReadContext(
                    validation_case_id=str(row["validation_case_id"]),
                    source_group_id=str(row["source_group_id"]),
                    specimen_group_id=(
                        str(row["specimen_group_id"])
                        if row["specimen_group_id"] is not None
                        else None
                    ),
                    read_sha256=read_sha256,
                    amplicon_id=(
                        str(row["amplicon_id"])
                        if row["amplicon_id"] is not None
                        else None
                    ),
                    declared_direction=(
                        str(row["declared_direction"])
                        if row["declared_direction"] is not None
                        else None
                    ),
                    orientation=selected_orientation,
                )
                contexts[read_sha256] = context
            else:
                if context.validation_case_id != row["validation_case_id"]:
                    raise ValueError(
                        f"{read_sha256}: validation case changes across rows"
                    )
                if context.orientation != selected_orientation:
                    raise ValueError(
                        f"{read_sha256}: selected orientation changes across rows"
                    )
            if position in tract_positions:
                context.tract_positions.add(position)

            if position in special_positions:
                if position in context.special_observations:
                    raise ValueError(
                        f"{read_sha256}: duplicate observation at position {position}"
                    )
                context.special_observations[position] = row

    return contexts, reference_bases, validate_reference_tracts(reference_bases)


def interrupt_fields(
    context: ReadContext,
    tract: PolyCTract,
) -> dict[str, Any]:
    row = context.special_observations.get(tract.interrupt_position_1based)
    if row is None:
        return {
            "interrupt_state": None,
            "interrupt_aligned_base": None,
            "interrupt_call_index_0based": None,
            "interrupt_profile_a": None,
            "interrupt_profile_c": None,
            "interrupt_profile_g": None,
            "interrupt_profile_t": None,
            "interrupt_in_noisy_region": None,
        }
    values = profile(row)
    return {
        "interrupt_state": row["state"],
        "interrupt_aligned_base": row["aligned_base"],
        "interrupt_call_index_0based": row["call_index_0based"],
        "interrupt_profile_a": values[0] if values is not None else None,
        "interrupt_profile_c": values[1] if values is not None else None,
        "interrupt_profile_g": values[2] if values is not None else None,
        "interrupt_profile_t": values[3] if values is not None else None,
        "interrupt_in_noisy_region": row["in_noisy_region"],
    }


def observation_record(
    row: dict[str, Any],
    context: ReadContext,
    tract: PolyCTract,
    reference_bases: dict[int, str],
) -> dict[str, Any]:
    position = int(row["position_1based"])
    region = path_region(tract, context.orientation, position)
    previous_position, next_position = reference_neighbor_positions(
        context.orientation,
        position,
    )
    previous_base = reference_bases.get(previous_position)
    next_base = reference_bases.get(next_position)
    values = profile(row)
    reference_base = str(row["reference_base"])

    previous_mass = (
        mass_for_base(values, previous_base)
        if values is not None and previous_base is not None
        else None
    )
    reference_mass = (
        mass_for_base(values, reference_base) if values is not None else None
    )
    next_mass = (
        mass_for_base(values, next_base)
        if values is not None and next_base is not None
        else None
    )
    impurity = 1.0 - max(values) if values is not None else None

    return {
        "validation_case_id": context.validation_case_id,
        "source_group_id": context.source_group_id,
        "specimen_group_id": context.specimen_group_id,
        "read_sha256": context.read_sha256,
        "amplicon_id": context.amplicon_id,
        "declared_direction": context.declared_direction,
        "orientation": context.orientation,
        "tract_id": tract.tract_id,
        "tract_start_1based": tract.start_1based,
        "tract_end_1based": tract.end_1based,
        "interrupt_position_1based": tract.interrupt_position_1based,
        "position_1based": position,
        "path_region": region,
        "read_order_distance_from_tract": read_order_distance(
            tract,
            context.orientation,
            position,
        ),
        "call_index_0based": row["call_index_0based"],
        "call_distance_from_tract": call_distance(context, tract, row, region),
        "reference_base": reference_base,
        "state": row["state"],
        "aligned_base": row["aligned_base"],
        "quality": row["quality"],
        "in_noisy_region": row["in_noisy_region"],
        "profile_a": values[0] if values is not None else None,
        "profile_c": values[1] if values is not None else None,
        "profile_g": values[2] if values is not None else None,
        "profile_t": values[3] if values is not None else None,
        "profile_impurity": impurity,
        "read_order_previous_reference_base": previous_base,
        "previous_reference_base_mass": previous_mass,
        "reference_base_mass": reference_mass,
        "read_order_next_reference_base": next_base,
        "next_reference_base_mass": next_mass,
        **interrupt_fields(context, tract),
    }


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def quantile(values: list[float], probability: float) -> float | None:
    return nearest_rank(values, probability) if values else None


def summary_rows(
    accumulators: dict[tuple[str, str, str, str, str], SummaryAccumulator],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in sorted(accumulators):
        tract_id, amplicon_id, selected_orientation, interrupt_base, region = key
        accumulator = accumulators[key]
        rows.append(
            {
                "tract_id": tract_id,
                "amplicon_id": amplicon_id,
                "orientation": selected_orientation,
                "interrupt_aligned_base": interrupt_base,
                "path_region": region,
                "observations": accumulator.observations,
                "profile_observations": len(accumulator.impurities),
                "noisy_observations": accumulator.noisy_observations,
                "mean_profile_impurity": mean(accumulator.impurities),
                "p50_profile_impurity": quantile(accumulator.impurities, 0.50),
                "p90_profile_impurity": quantile(accumulator.impurities, 0.90),
                "mean_previous_reference_base_mass": mean(accumulator.previous_masses),
                "p50_previous_reference_base_mass": quantile(
                    accumulator.previous_masses, 0.50
                ),
                "p90_previous_reference_base_mass": quantile(
                    accumulator.previous_masses, 0.90
                ),
                "mean_next_reference_base_mass": mean(accumulator.next_masses),
                "p50_next_reference_base_mass": quantile(accumulator.next_masses, 0.50),
                "p90_next_reference_base_mass": quantile(accumulator.next_masses, 0.90),
            }
        )
    return rows


def research_index(
    corpus: ResearchCorpus,
    active_tracts: tuple[PolyCTract, ...],
    observations_path: Path,
    summary_path: Path,
    observation_count: int,
    summary_count: int,
    crossing_reads: int,
) -> dict[str, Any]:
    return {
        "schema_version": POLYC_PHASE_SCHEMA_VERSION,
        "source_corpus_sha256": file_sha256(corpus.index_path),
        "signal_version": corpus.signal_version,
        "manifest_sha256": corpus.manifest_sha256,
        "reference_sha256": corpus.reference_sha256,
        "configuration_sha256": corpus.configuration_sha256,
        "method": {
            "reference_topology": "rCRS",
            "tracts": [
                {
                    "tract_id": tract.tract_id,
                    "start_1based": tract.start_1based,
                    "end_1based": tract.end_1based,
                    "interrupt_position_1based": tract.interrupt_position_1based,
                    "reference_sequence": tract.reference_sequence,
                }
                for tract in active_tracts
            ],
            "read_crossing_rule": (
                "selected read span covers every reference position from tract start "
                "through tract end"
            ),
            "distance_rule": (
                "signed reference distance in sequencing order: negative before tract, "
                "zero inside tract, positive after tract"
            ),
            "summary_quantile_method": "empirical_nearest_rank",
        },
        "crossing_reads": crossing_reads,
        "observations_file": "observations.csv",
        "observations_sha256": file_sha256(observations_path),
        "observations_rows": observation_count,
        "observations_columns": list(OBSERVATION_COLUMNS),
        "summary_file": "summary.csv",
        "summary_sha256": file_sha256(summary_path),
        "summary_rows": summary_count,
        "summary_columns": list(SUMMARY_COLUMNS),
    }


def build_staged_polyc_phase(corpus: ResearchCorpus, stage: Path) -> None:
    contexts, reference_bases, active_tracts = scan_context(corpus)
    crossing = {
        (read_sha256, tract.tract_id)
        for read_sha256, context in contexts.items()
        for tract in active_tracts
        if read_crosses_tract(context, tract)
    }
    if not crossing:
        raise ValueError("no validation read spans a supported rCRS poly-C tract")

    observations_path = stage / "observations.csv"
    summary_path = stage / "summary.csv"
    accumulators: dict[
        tuple[str, str, str, str, str],
        SummaryAccumulator,
    ] = {}
    observation_count = 0

    with observations_path.open("x", encoding="utf-8", newline="") as target:
        observations_writer = writer(target, OBSERVATION_COLUMNS)
        for _, observation_rows in iter_research_rows(corpus):
            for source in observation_rows:
                read_sha256 = str(source["read_sha256"])
                context = contexts[read_sha256]
                for tract in active_tracts:
                    if (read_sha256, tract.tract_id) not in crossing:
                        continue
                    row = observation_record(source, context, tract, reference_bases)
                    write_row(
                        observations_writer,
                        row,
                        OBSERVATION_COLUMNS,
                        f"poly-C observation row {observation_count}",
                    )
                    key = (
                        tract.tract_id,
                        context.amplicon_id or "",
                        context.orientation,
                        str(row["interrupt_aligned_base"] or ""),
                        str(row["path_region"]),
                    )
                    accumulators.setdefault(key, SummaryAccumulator()).add(row)
                    observation_count += 1
        target.flush()
        os.fsync(target.fileno())

    summaries = summary_rows(accumulators)
    with summary_path.open("x", encoding="utf-8", newline="") as target:
        summary_writer = writer(target, SUMMARY_COLUMNS)
        for index, row in enumerate(summaries):
            write_row(summary_writer, row, SUMMARY_COLUMNS, f"summary row {index}")
        target.flush()
        os.fsync(target.fileno())

    write_json(
        stage / "index.json",
        research_index(
            corpus,
            active_tracts,
            observations_path,
            summary_path,
            observation_count,
            len(summaries),
            len(crossing),
        ),
    )
    sync_directory(stage)


def publish_polyc_phase(corpus_dir: Path, output_dir: Path) -> None:
    corpus_dir = corpus_dir.resolve()
    output_dir = output_dir.resolve()
    if not corpus_dir.is_dir():
        raise ValueError(f"corpus directory does not exist: {corpus_dir}")
    validate_new_directory(output_dir, (corpus_dir,))
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if not output_dir.parent.is_dir() or output_dir.parent.is_symlink():
        raise ValueError(
            f"output parent is not a regular directory: {output_dir.parent}"
        )

    corpus = load_research_corpus(corpus_dir)
    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        build_staged_polyc_phase(corpus, stage)
        try:
            output_dir.mkdir()
        except FileExistsError as error:
            raise FileExistsError(
                f"output directory appeared while poly-C research was running: "
                f"{output_dir}"
            ) from error
        try:
            for name in ("observations.csv", "summary.csv", "index.json"):
                os.rename(stage / name, output_dir / name)
            sync_directory(output_dir)
            sync_directory(output_dir.parent)
        except OSError:
            shutil.rmtree(output_dir, ignore_errors=True)
            sync_directory(output_dir.parent)
            raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
