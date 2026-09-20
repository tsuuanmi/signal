"""Descriptive mtDNA poly-C phase-instability research from validation measurements."""

from __future__ import annotations

import csv
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO

from .filesystem import file_sha256, sync_directory, validate_new_directory, write_json
from .model import POLYC_PHASE_SCHEMA_VERSION
from .polyc_context import (
    ReadContext,
    crossing_spans,
    mass_for_base,
    profile,
    scan_context,
)
from .polyc_geometry import (
    PolyCTract,
    TractCallSpan,
    call_distance,
    path_region,
    read_order_distance,
    reference_neighbor_positions,
)
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


def interrupt_fields(
    context: ReadContext,
    tract: PolyCTract,
) -> dict[str, Any]:
    row = context.tract_observations.get(tract.interrupt_position_1based)
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
    span: TractCallSpan,
    reference_bases: dict[int, str],
) -> dict[str, Any]:
    position = int(row["position_1based"])
    raw_call_index = row["call_index_0based"]
    call_index = int(raw_call_index) if raw_call_index is not None else None
    region = path_region(tract, position, call_index, span)
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
            region,
        ),
        "call_index_0based": call_index,
        "call_distance_from_tract": call_distance(span, call_index, region),
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
                "the read has a validation observation at every reference position "
                "from tract start through tract end"
            ),
            "distance_rule": (
                "before/after derives from call order relative to the complete tract "
                "call span; signed reference distance follows circular rCRS sequencing "
                "order; non-call-backed outside-tract observations are unresolved"
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
    crossing = crossing_spans(contexts, active_tracts)
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
                    row = observation_record(
                        source,
                        context,
                        tract,
                        crossing[(read_sha256, tract.tract_id)],
                        reference_bases,
                    )
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
