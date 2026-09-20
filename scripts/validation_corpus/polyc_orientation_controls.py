"""Matched opposite-orientation controls for mtDNA poly-C validation research."""

from __future__ import annotations

import csv
import math
import os
import shutil
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO

from .filesystem import file_sha256, sync_directory, validate_new_directory, write_json
from .model import POLYC_ORIENTATION_CONTROL_SCHEMA_VERSION
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
)
from .research_loader import iter_research_rows, load_research_corpus
from .research_model import ResearchCorpus

OBSERVATION_COLUMNS = (
    "control_id",
    "validation_case_id",
    "source_group_id",
    "specimen_group_id",
    "tract_id",
    "position_1based",
    "reference_base",
    "post_orientation",
    "role",
    "read_sha256",
    "orientation",
    "pcr_replicate_id",
    "sequencing_run_id",
    "instrument_id",
    "amplicon_id",
    "declared_direction",
    "artifact_tags",
    "path_region",
    "call_index_0based",
    "read_order_distance_from_tract",
    "call_distance_from_tract",
    "state",
    "aligned_base",
    "quality",
    "in_noisy_region",
    "profile_a",
    "profile_c",
    "profile_g",
    "profile_t",
    "profile_impurity",
    "reference_base_mass",
)

LOCUS_COLUMNS = (
    "control_id",
    "validation_case_id",
    "source_group_id",
    "specimen_group_id",
    "tract_id",
    "position_1based",
    "reference_base",
    "post_orientation",
    "post_reads",
    "control_reads",
    "post_profile_reads",
    "control_profile_reads",
    "post_noisy_observations",
    "control_noisy_observations",
    "mean_post_profile_impurity",
    "mean_control_profile_impurity",
    "mean_post_reference_base_mass",
    "mean_control_reference_base_mass",
    "mean_post_a",
    "mean_post_c",
    "mean_post_g",
    "mean_post_t",
    "mean_control_a",
    "mean_control_c",
    "mean_control_g",
    "mean_control_t",
    "mean_profile_total_variation",
)


@dataclass(frozen=True)
class ClassifiedObservation:
    source: dict[str, Any]
    context: ReadContext
    span: TractCallSpan
    region: str


@dataclass
class RoleAccumulator:
    reads: int = 0
    noisy_observations: int = 0
    profiles: list[tuple[float, float, float, float]] = field(default_factory=list)
    impurities: list[float] = field(default_factory=list)
    reference_masses: list[float] = field(default_factory=list)

    def add(self, row: dict[str, Any]) -> None:
        self.reads += 1
        if row["in_noisy_region"] is True:
            self.noisy_observations += 1
        values = tuple(row[f"profile_{base}"] for base in ("a", "c", "g", "t"))
        if all(value is None for value in values):
            return
        if any(value is None for value in values):
            raise ValueError("control observation profile is partially missing")
        parsed = tuple(float(value) for value in values)
        self.profiles.append((parsed[0], parsed[1], parsed[2], parsed[3]))
        impurity = row["profile_impurity"]
        reference_mass = row["reference_base_mass"]
        if impurity is None or reference_mass is None:
            raise ValueError(
                "profile-bearing control observation lacks derived metrics"
            )
        self.impurities.append(float(impurity))
        self.reference_masses.append(float(reference_mass))


def opposite_orientation(selected_orientation: str) -> str:
    if selected_orientation == "forward":
        return "reverse"
    if selected_orientation == "reverse":
        return "forward"
    raise ValueError(f"unsupported orientation {selected_orientation!r}")


def mean(values: list[float]) -> float | None:
    return math.fsum(values) / len(values) if values else None


def mean_profile(
    profiles: list[tuple[float, float, float, float]],
) -> tuple[float, float, float, float] | None:
    if not profiles:
        return None
    count = len(profiles)
    means = [
        math.fsum(values[channel] for values in profiles) / count
        for channel in range(4)
    ]
    return means[0], means[1], means[2], means[3]


def total_variation(
    left: tuple[float, float, float, float] | None,
    right: tuple[float, float, float, float] | None,
) -> float | None:
    if left is None or right is None:
        return None
    return 0.5 * math.fsum(
        abs(left_value - right_value)
        for left_value, right_value in zip(left, right, strict=True)
    )


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def writer(target: TextIO, columns: tuple[str, ...]) -> csv.DictWriter:
    fieldnames: list[str] = list(columns)
    built = csv.DictWriter(
        target,
        fieldnames=fieldnames,
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
            f"{label} does not match output columns: missing={missing} extra={extra}"
        )
    target.writerow({key: csv_value(row[key]) for key in columns})


def classify_observation(
    source: dict[str, Any],
    context: ReadContext,
    tract: PolyCTract,
    span: TractCallSpan,
) -> ClassifiedObservation:
    raw_call_index = source["call_index_0based"]
    call_index = int(raw_call_index) if raw_call_index is not None else None
    region = path_region(
        tract,
        int(source["position_1based"]),
        call_index,
        span,
    )
    return ClassifiedObservation(source, context, span, region)


def iter_matched_groups(
    corpus: ResearchCorpus,
    contexts: dict[str, ReadContext],
    active_tracts: tuple[PolyCTract, ...],
    spans: dict[tuple[str, str], TractCallSpan],
) -> Iterator[
    tuple[
        str,
        PolyCTract,
        int,
        str,
        list[ClassifiedObservation],
        list[ClassifiedObservation],
    ]
]:
    for locus_row, observation_rows in iter_research_rows(corpus):
        case_id = str(locus_row["validation_case_id"])
        position = int(locus_row["position_1based"])
        classified_by_tract: dict[str, list[ClassifiedObservation]] = {
            tract.tract_id: [] for tract in active_tracts
        }

        for source in observation_rows:
            read_sha256 = str(source["read_sha256"])
            context = contexts[read_sha256]
            if context.validation_case_id != case_id:
                raise ValueError(f"{read_sha256}: locus/case identity mismatch")
            for tract in active_tracts:
                span = spans.get((read_sha256, tract.tract_id))
                if span is None:
                    continue
                classified_by_tract[tract.tract_id].append(
                    classify_observation(source, context, tract, span)
                )

        for tract in active_tracts:
            classified = classified_by_tract[tract.tract_id]
            for post_orientation in ("forward", "reverse"):
                control_orientation = opposite_orientation(post_orientation)
                posts = sorted(
                    (
                        item
                        for item in classified
                        if item.context.orientation == post_orientation
                        and item.region == "after"
                    ),
                    key=lambda item: item.context.read_sha256,
                )
                controls = sorted(
                    (
                        item
                        for item in classified
                        if item.context.orientation == control_orientation
                        and item.region == "before"
                    ),
                    key=lambda item: item.context.read_sha256,
                )
                if posts and controls:
                    yield (
                        case_id,
                        tract,
                        position,
                        post_orientation,
                        posts,
                        controls,
                    )


def observation_row(
    control_id: str,
    tract: PolyCTract,
    position: int,
    reference_base: str,
    post_orientation: str,
    role: str,
    item: ClassifiedObservation,
) -> dict[str, Any]:
    source = item.source
    context = item.context
    raw_call_index = source["call_index_0based"]
    call_index = int(raw_call_index) if raw_call_index is not None else None
    values = profile(source)
    impurity = 1.0 - max(values) if values is not None else None
    reference_mass = (
        mass_for_base(values, reference_base) if values is not None else None
    )
    return {
        "control_id": control_id,
        "validation_case_id": context.validation_case_id,
        "source_group_id": context.source_group_id,
        "specimen_group_id": context.specimen_group_id,
        "tract_id": tract.tract_id,
        "position_1based": position,
        "reference_base": reference_base,
        "post_orientation": post_orientation,
        "role": role,
        "read_sha256": context.read_sha256,
        "orientation": context.orientation,
        "pcr_replicate_id": context.pcr_replicate_id,
        "sequencing_run_id": context.sequencing_run_id,
        "instrument_id": context.instrument_id,
        "amplicon_id": context.amplicon_id,
        "declared_direction": context.declared_direction,
        "artifact_tags": context.artifact_tags,
        "path_region": item.region,
        "call_index_0based": call_index,
        "read_order_distance_from_tract": read_order_distance(
            tract,
            context.orientation,
            position,
            item.region,
        ),
        "call_distance_from_tract": call_distance(
            item.span,
            call_index,
            item.region,
        ),
        "state": source["state"],
        "aligned_base": source["aligned_base"],
        "quality": source["quality"],
        "in_noisy_region": source["in_noisy_region"],
        "profile_a": values[0] if values is not None else None,
        "profile_c": values[1] if values is not None else None,
        "profile_g": values[2] if values is not None else None,
        "profile_t": values[3] if values is not None else None,
        "profile_impurity": impurity,
        "reference_base_mass": reference_mass,
    }


def locus_row(
    control_id: str,
    case_id: str,
    tract: PolyCTract,
    position: int,
    reference_base: str,
    post_orientation: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    post = RoleAccumulator()
    control = RoleAccumulator()
    source_group_id: str | None = None
    specimen_group_id: str | None = None

    for row in rows:
        row_source_group = str(row["source_group_id"])
        row_specimen = (
            str(row["specimen_group_id"])
            if row["specimen_group_id"] is not None
            else None
        )
        if source_group_id is None:
            source_group_id = row_source_group
            specimen_group_id = row_specimen
        elif source_group_id != row_source_group or specimen_group_id != row_specimen:
            raise ValueError(
                f"{control_id}: case grouping metadata changes across reads"
            )

        role = row["role"]
        if role == "post_tract":
            post.add(row)
        elif role == "pre_tract_opposite_control":
            control.add(row)
        else:
            raise ValueError(f"{control_id}: unsupported role {role!r}")

    if source_group_id is None or post.reads == 0 or control.reads == 0:
        raise ValueError(f"{control_id}: matched control group is incomplete")

    post_profile = mean_profile(post.profiles)
    control_profile = mean_profile(control.profiles)

    return {
        "control_id": control_id,
        "validation_case_id": case_id,
        "source_group_id": source_group_id,
        "specimen_group_id": specimen_group_id,
        "tract_id": tract.tract_id,
        "position_1based": position,
        "reference_base": reference_base,
        "post_orientation": post_orientation,
        "post_reads": post.reads,
        "control_reads": control.reads,
        "post_profile_reads": len(post.profiles),
        "control_profile_reads": len(control.profiles),
        "post_noisy_observations": post.noisy_observations,
        "control_noisy_observations": control.noisy_observations,
        "mean_post_profile_impurity": mean(post.impurities),
        "mean_control_profile_impurity": mean(control.impurities),
        "mean_post_reference_base_mass": mean(post.reference_masses),
        "mean_control_reference_base_mass": mean(control.reference_masses),
        "mean_post_a": post_profile[0] if post_profile is not None else None,
        "mean_post_c": post_profile[1] if post_profile is not None else None,
        "mean_post_g": post_profile[2] if post_profile is not None else None,
        "mean_post_t": post_profile[3] if post_profile is not None else None,
        "mean_control_a": control_profile[0] if control_profile is not None else None,
        "mean_control_c": control_profile[1] if control_profile is not None else None,
        "mean_control_g": control_profile[2] if control_profile is not None else None,
        "mean_control_t": control_profile[3] if control_profile is not None else None,
        "mean_profile_total_variation": total_variation(
            post_profile,
            control_profile,
        ),
    }


def output_index(
    corpus: ResearchCorpus,
    active_tracts: tuple[PolyCTract, ...],
    observations_path: Path,
    loci_path: Path,
    observation_count: int,
    locus_count: int,
) -> dict[str, Any]:
    return {
        "schema_version": POLYC_ORIENTATION_CONTROL_SCHEMA_VERSION,
        "source_corpus_sha256": file_sha256(corpus.index_path),
        "signal_version": corpus.signal_version,
        "manifest_sha256": corpus.manifest_sha256,
        "reference_sha256": corpus.reference_sha256,
        "configuration_sha256": corpus.configuration_sha256,
        "method": {
            "reference_topology": "rCRS",
            "tracts": [tract.tract_id for tract in active_tracts],
            "matching_key": (
                "validation_case_id x tract_id x position_1based x post_orientation"
            ),
            "role_rule": (
                "post_tract requires a complete-tract read after the tract in selected "
                "call order; control requires an opposite selected-orientation "
                "complete-tract read before the tract at the same case/locus"
            ),
            "orientation_source": "selected alignment orientation; never declared_direction",
            "read_selection": "retain every eligible read; no pair or winner selection",
            "mean_profile_distance": "total_variation = 0.5 * sum(abs(post_i-control_i))",
            "thresholds": "none",
        },
        "matched_loci": locus_count,
        "observations_file": "observations.csv",
        "observations_sha256": file_sha256(observations_path),
        "observations_rows": observation_count,
        "observations_columns": list(OBSERVATION_COLUMNS),
        "loci_file": "loci.csv",
        "loci_sha256": file_sha256(loci_path),
        "loci_rows": locus_count,
        "loci_columns": list(LOCUS_COLUMNS),
    }


def build_staged_orientation_controls(corpus: ResearchCorpus, stage: Path) -> None:
    contexts, reference_bases, active_tracts = scan_context(corpus)
    spans = crossing_spans(contexts, active_tracts)
    if not spans:
        raise ValueError("no validation read spans a supported rCRS poly-C tract")

    observations_path = stage / "observations.csv"
    loci_path = stage / "loci.csv"
    observation_count = 0
    locus_count = 0

    with (
        observations_path.open("x", encoding="utf-8", newline="") as observations_file,
        loci_path.open("x", encoding="utf-8", newline="") as loci_file,
    ):
        observations_writer = writer(observations_file, OBSERVATION_COLUMNS)
        loci_writer = writer(loci_file, LOCUS_COLUMNS)

        for (
            case_id,
            tract,
            position,
            post_orientation,
            posts,
            controls,
        ) in iter_matched_groups(corpus, contexts, active_tracts, spans):
            reference_base = reference_bases.get(position)
            if reference_base is None:
                raise ValueError(f"missing reference base at matched locus {position}")
            control_id = f"{case_id}:{tract.tract_id}:{position}:{post_orientation}"
            rows: list[dict[str, Any]] = []
            for role, items in (
                ("post_tract", posts),
                ("pre_tract_opposite_control", controls),
            ):
                for item in items:
                    row = observation_row(
                        control_id,
                        tract,
                        position,
                        reference_base,
                        post_orientation,
                        role,
                        item,
                    )
                    write_row(
                        observations_writer,
                        row,
                        OBSERVATION_COLUMNS,
                        f"orientation-control observation {observation_count}",
                    )
                    rows.append(row)
                    observation_count += 1

            summary = locus_row(
                control_id,
                case_id,
                tract,
                position,
                reference_base,
                post_orientation,
                rows,
            )
            write_row(
                loci_writer,
                summary,
                LOCUS_COLUMNS,
                f"orientation-control locus {locus_count}",
            )
            locus_count += 1

        if locus_count == 0:
            raise ValueError("no matched opposite-orientation poly-C control loci")

        observations_file.flush()
        os.fsync(observations_file.fileno())
        loci_file.flush()
        os.fsync(loci_file.fileno())

    write_json(
        stage / "index.json",
        output_index(
            corpus,
            active_tracts,
            observations_path,
            loci_path,
            observation_count,
            locus_count,
        ),
    )
    sync_directory(stage)


def publish_polyc_orientation_controls(
    corpus_dir: Path,
    output_dir: Path,
) -> None:
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
        build_staged_orientation_controls(corpus, stage)
        try:
            output_dir.mkdir()
        except FileExistsError as error:
            raise FileExistsError(
                "output directory appeared while orientation controls were running: "
                f"{output_dir}"
            ) from error
        try:
            for name in ("observations.csv", "loci.csv", "index.json"):
                os.rename(stage / name, output_dir / name)
            sync_directory(output_dir)
            sync_directory(output_dir.parent)
        except OSError:
            shutil.rmtree(output_dir, ignore_errors=True)
            sync_directory(output_dir.parent)
            raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
