"""Attribute biological variant-profile disagreements to exact phase evidence."""

from __future__ import annotations

import csv
import hashlib
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO

from .filesystem import file_sha256, sync_directory, validate_new_directory, write_json
from .model import (
    VARIANT_PHASE_CONTEXT_SCHEMA_VERSION,
    VARIANT_PROFILE_EVALUATION_SCHEMA_VERSION,
)
from .phase_hypotheses import candidate_contribution
from .phase_interpretation_dataset import (
    PARTITIONS,
    PartitionPlan,
    case_map,
    partition_for,
    validate_declared_groups,
)
from .phase_recurrent_loci import membership_map, validate_source_pair
from .research_loader import json_object, load_research_corpus, strict_keys
from .research_model import ResearchCase, ResearchCorpus
from .variant_profile_evaluation import DIFFERENCE_COLUMNS, SAMPLE_COLUMNS

EVALUATION_INDEX_FIELDS = (
    "schema_version",
    "truth_status",
    "source_ground_truth_sha256",
    "configuration_sha256",
    "reference",
    "method",
    "summary",
    "samples_file",
    "samples_sha256",
    "samples_rows",
    "samples_columns",
    "differences_file",
    "differences_sha256",
    "differences_rows",
    "differences_columns",
)

DIFFERENCE_COLUMNS_OUT = (
    "difference_id",
    "sample_id",
    "validation_case_id",
    "difference",
    "event_kind",
    "event_position_1based",
    "event_reference",
    "event_alternate",
    "reference_footprint_start_1based",
    "reference_footprint_end_1based",
    "insertion_boundary_after_1based",
    "source_events",
    "phase_observations",
    "phase_reads",
    "exact_phase_windows",
)

OBSERVATION_COLUMNS = (
    "difference_id",
    "sample_id",
    "validation_case_id",
    "difference",
    "event_kind",
    "event_position_1based",
    "reference_footprint_start_1based",
    "reference_footprint_end_1based",
    "read_sha256",
    "source_group_id",
    "specimen_group_id",
    "pcr_replicate_id",
    "sequencing_run_id",
    "instrument_id",
    "amplicon_id",
    "declared_direction",
    "artifact_tags",
    "tract_id",
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
    "containing_windows",
)

WINDOW_COLUMNS = (
    "difference_id",
    "validation_case_id",
    "read_sha256",
    "tract_id",
    "position_1based",
    "read_order_distance_from_tract",
    "window_id",
    "window_start_distance_after_tract",
    "window_end_distance_after_tract",
    "window_start_call_index_0based",
    "window_end_call_index_0based",
    "window_profile_observations",
    "window_noisy_observations",
    "window_mean_profile_impurity",
    "window_mean_zero_reference_mass",
)

CANDIDATE_COLUMNS = (
    "difference_id",
    "validation_case_id",
    "read_sha256",
    "tract_id",
    "position_1based",
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

READINESS_COLUMNS = (
    "partition",
    "difference",
    "cases",
    "biological_differences",
    "fit_eligible_differences",
    "phase_observations",
    "phase_reads",
    "exact_phase_windows",
)


@dataclass(frozen=True)
class VariantEvent:
    kind: str
    position: int
    reference: str
    alternate: str


@dataclass
class ReadinessCounts:
    cases: set[str] = field(default_factory=set)
    differences: int = 0
    fit_eligible_differences: int = 0
    phase_observations: int = 0
    phase_reads: set[str] = field(default_factory=set)
    phase_windows: set[str] = field(default_factory=set)


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


def nonnegative_index_count(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def validate_csv(
    path: Path,
    columns: tuple[str, ...],
    expected_rows: int,
    expected_sha256: str,
) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"evaluation table is not a regular file: {path}")
    if file_sha256(path) != expected_sha256:
        raise ValueError(f"{path.name} SHA-256 mismatch")
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or tuple(reader.fieldnames) != columns:
            raise ValueError(f"{path}: unexpected columns")
        rows = list(reader)
    if len(rows) != expected_rows:
        raise ValueError(f"{path}: expected {expected_rows} rows, found {len(rows)}")
    return rows


def load_evaluation(
    evaluation_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    index_path = evaluation_dir / "index.json"
    if not index_path.is_file():
        raise ValueError(f"variant-profile evaluation index is missing: {index_path}")
    index = json_object(index_path)
    strict_keys(index, EVALUATION_INDEX_FIELDS, "variant-profile evaluation index")
    if index["schema_version"] != VARIANT_PROFILE_EVALUATION_SCHEMA_VERSION:
        raise ValueError(
            "unsupported variant-profile evaluation schema: "
            f"{index['schema_version']!r}"
        )
    if index["samples_file"] != "samples.csv":
        raise ValueError("variant-profile samples_file must be samples.csv")
    if index["differences_file"] != "differences.csv":
        raise ValueError("variant-profile differences_file must be differences.csv")
    if index["samples_columns"] != list(SAMPLE_COLUMNS):
        raise ValueError("variant-profile samples_columns differ from current contract")
    if index["differences_columns"] != list(DIFFERENCE_COLUMNS):
        raise ValueError(
            "variant-profile differences_columns differ from current contract"
        )
    samples_rows = nonnegative_index_count(index["samples_rows"], "samples_rows")
    differences_rows = nonnegative_index_count(
        index["differences_rows"], "differences_rows"
    )
    validate_csv(
        evaluation_dir / "samples.csv",
        SAMPLE_COLUMNS,
        samples_rows,
        str(index["samples_sha256"]),
    )
    differences = validate_csv(
        evaluation_dir / "differences.csv",
        DIFFERENCE_COLUMNS,
        differences_rows,
        str(index["differences_sha256"]),
    )
    return index, differences


def parse_event(text: str) -> VariantEvent:
    try:
        prefix, alternate = text.split(">", 1)
        kind, raw_position, reference = prefix.split(":", 2)
        position = int(raw_position)
    except (ValueError, TypeError) as error:
        raise ValueError(f"invalid normalized variant event: {text!r}") from error
    if kind not in {"SNV", "INS", "DEL"}:
        raise ValueError(f"unsupported normalized variant event kind: {kind!r}")
    if position < 1 or not reference or alternate == "":
        raise ValueError(f"invalid normalized variant event: {text!r}")
    return VariantEvent(kind, position, reference, alternate)


def selected_event(row: dict[str, str]) -> tuple[VariantEvent, str]:
    difference = row["difference"]
    if difference == "missing":
        source = row["reviewer_events"]
    elif difference == "extra":
        source = row["signal_events"]
    else:
        raise ValueError(
            f"only biological missing/extra differences may be attributed, got {difference!r}"
        )
    events = [parse_event(value) for value in source.split("|") if value]
    if len(events) != 1:
        raise ValueError(
            "biological difference must contain exactly one unmatched source event"
        )
    return events[0], source


def event_footprint(
    event: VariantEvent, reference_length: int
) -> tuple[int, int, int | None]:
    end = event.position + len(event.reference) - 1
    if end > reference_length:
        raise ValueError("variant event reference footprint exceeds reference length")
    insertion_boundary = event.position if event.kind == "INS" else None
    return event.position, end, insertion_boundary


def difference_id(row: dict[str, str], source_events: str) -> str:
    payload = "\0".join(
        (
            row["sample_id"],
            row["validation_case_id"],
            row["difference"],
            source_events,
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def validate_provenance(
    corpus: ResearchCorpus,
    evaluation_index: dict[str, Any],
    phase_index: dict[str, Any],
) -> None:
    reference = evaluation_index["reference"]
    if not isinstance(reference, dict):
        raise TypeError("variant-profile evaluation reference must be an object")
    if reference.get("sha256") != corpus.reference_sha256:
        raise ValueError("variant-profile evaluation reference differs from corpus")
    if evaluation_index["configuration_sha256"] != corpus.configuration_sha256:
        raise ValueError("variant-profile evaluation configuration differs from corpus")
    if phase_index["source_corpus_sha256"] != file_sha256(corpus.index_path):
        raise ValueError("poly-C phase source corpus differs from supplied corpus")
    for key, expected in (
        ("signal_version", corpus.signal_version),
        ("manifest_sha256", corpus.manifest_sha256),
        ("reference_sha256", corpus.reference_sha256),
        ("configuration_sha256", corpus.configuration_sha256),
    ):
        if phase_index[key] != expected:
            raise ValueError(f"poly-C phase {key} differs from supplied corpus")


def profile_values(observation: Any) -> tuple[Any, Any, Any, Any]:
    if observation.profile is None:
        return None, None, None, None
    return observation.profile


def observation_row(
    difference: dict[str, Any],
    case: ResearchCase,
    observation: Any,
    containing: list[str],
) -> dict[str, Any]:
    read = case.reads[observation.read_sha256]
    profile_a, profile_c, profile_g, profile_t = profile_values(observation)
    return {
        "difference_id": difference["difference_id"],
        "sample_id": difference["sample_id"],
        "validation_case_id": difference["validation_case_id"],
        "difference": difference["difference"],
        "event_kind": difference["event_kind"],
        "event_position_1based": difference["event_position_1based"],
        "reference_footprint_start_1based": difference[
            "reference_footprint_start_1based"
        ],
        "reference_footprint_end_1based": difference["reference_footprint_end_1based"],
        "read_sha256": observation.read_sha256,
        "source_group_id": case.metadata["source_group_id"],
        "specimen_group_id": case.metadata["specimen_group_id"],
        "pcr_replicate_id": read["pcr_replicate_id"],
        "sequencing_run_id": read["sequencing_run_id"],
        "instrument_id": read["instrument_id"],
        "amplicon_id": read["amplicon_id"],
        "declared_direction": read["declared_direction"],
        "artifact_tags": ";".join(read["artifact_tags"]),
        "tract_id": observation.tract_id,
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
        "containing_windows": len(containing),
    }


def window_row(
    difference_id_value: str,
    observation: Any,
    source: Any,
) -> dict[str, Any]:
    return {
        "difference_id": difference_id_value,
        "validation_case_id": observation.validation_case_id,
        "read_sha256": observation.read_sha256,
        "tract_id": observation.tract_id,
        "position_1based": observation.position_1based,
        "read_order_distance_from_tract": observation.distance,
        "window_id": source.window_id,
        "window_start_distance_after_tract": source.start_distance,
        "window_end_distance_after_tract": source.end_distance,
        "window_start_call_index_0based": source.start_call_index,
        "window_end_call_index_0based": source.end_call_index,
        "window_profile_observations": source.profile_observations,
        "window_noisy_observations": source.noisy_observations,
        "window_mean_profile_impurity": source.mean_profile_impurity,
        "window_mean_zero_reference_mass": source.mean_zero_reference_mass,
    }


def candidate_row(
    difference_id_value: str,
    observation: Any,
    window_id: str,
    candidate: Any,
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
        "difference_id": difference_id_value,
        "validation_case_id": observation.validation_case_id,
        "read_sha256": observation.read_sha256,
        "tract_id": observation.tract_id,
        "position_1based": observation.position_1based,
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
    corpus: ResearchCorpus,
    differences: list[dict[str, str]],
    reference_length: int,
    plan: PartitionPlan,
    groups: dict[tuple[str, str], list[Any]],
    generated_windows: list[Any],
    source_windows: dict[str, Any],
    candidates: dict[tuple[str, int], Any],
    offsets: tuple[int, ...],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    mapping = plan.mapping()
    validate_declared_groups(corpus, mapping)
    cases = case_map(corpus)
    memberships = membership_map(generated_windows)
    references = {
        key: {observation.distance: observation.reference_base for observation in rows}
        for key, rows in groups.items()
    }
    observations_by_case: dict[str, list[Any]] = {}
    for rows in groups.values():
        for observation in rows:
            observations_by_case.setdefault(observation.validation_case_id, []).append(
                observation
            )

    detailed_differences: list[dict[str, Any]] = []
    observation_rows: list[dict[str, Any]] = []
    window_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    readiness: dict[tuple[str, str], ReadinessCounts] = {}

    for row in differences:
        if row["difference"] == "representation":
            continue
        event, source_events = selected_event(row)
        case_id = row["validation_case_id"]
        case = cases.get(case_id)
        if case is None:
            raise ValueError(
                f"variant-profile difference references unknown validation case {case_id!r}"
            )
        partition = partition_for(str(case.metadata["holdout_group"]), mapping)
        key = (partition, row["difference"])
        counts = readiness.setdefault(key, ReadinessCounts())
        counts.cases.add(case_id)
        counts.differences += 1

        start, end, insertion_boundary = event_footprint(event, reference_length)
        id_value = difference_id(row, source_events)
        related = sorted(
            (
                observation
                for observation in observations_by_case.get(case_id, [])
                if start <= observation.position_1based <= end
            ),
            key=lambda observation: (
                observation.position_1based,
                observation.read_sha256,
                observation.tract_id,
                observation.distance,
            ),
        )

        related_windows: set[str] = set()
        for observation in related:
            membership_key = (
                observation.read_sha256,
                observation.tract_id,
                observation.distance,
            )
            related_windows.update(memberships.get(membership_key, ()))
        counts.phase_observations += len(related)
        counts.phase_reads.update(observation.read_sha256 for observation in related)
        counts.phase_windows.update(related_windows)

        fit_eligible = (
            partition == "development"
            and case.metadata["include_in_threshold_fit"] is True
        )
        if not fit_eligible:
            continue
        counts.fit_eligible_differences += 1

        difference_record = {
            "difference_id": id_value,
            "sample_id": row["sample_id"],
            "validation_case_id": case_id,
            "difference": row["difference"],
            "event_kind": event.kind,
            "event_position_1based": event.position,
            "event_reference": event.reference,
            "event_alternate": event.alternate,
            "reference_footprint_start_1based": start,
            "reference_footprint_end_1based": end,
            "insertion_boundary_after_1based": insertion_boundary,
            "source_events": source_events,
            "phase_observations": len(related),
            "phase_reads": len({observation.read_sha256 for observation in related}),
            "exact_phase_windows": len(related_windows),
        }
        detailed_differences.append(difference_record)

        for observation in related:
            membership_key = (
                observation.read_sha256,
                observation.tract_id,
                observation.distance,
            )
            containing = memberships.get(membership_key, [])
            observation_rows.append(
                observation_row(difference_record, case, observation, containing)
            )
            reference_by_distance = references[
                (observation.read_sha256, observation.tract_id)
            ]
            for window_id in containing:
                source = source_windows[window_id]
                window_rows.append(window_row(id_value, observation, source))
                for offset in offsets:
                    candidate_rows.append(
                        candidate_row(
                            id_value,
                            observation,
                            window_id,
                            candidates[(window_id, offset)],
                            reference_by_distance,
                        )
                    )

    detailed_differences.sort(
        key=lambda row: (
            str(row["validation_case_id"]),
            str(row["difference"]),
            int(row["event_position_1based"]),
            str(row["difference_id"]),
        )
    )
    observation_rows.sort(
        key=lambda row: (
            str(row["difference_id"]),
            int(row["position_1based"]),
            str(row["read_sha256"]),
            str(row["tract_id"]),
            int(row["read_order_distance_from_tract"]),
        )
    )
    window_rows.sort(
        key=lambda row: (
            str(row["difference_id"]),
            str(row["read_sha256"]),
            str(row["tract_id"]),
            int(row["position_1based"]),
            str(row["window_id"]),
        )
    )
    candidate_rows.sort(
        key=lambda row: (
            str(row["difference_id"]),
            str(row["read_sha256"]),
            str(row["tract_id"]),
            int(row["position_1based"]),
            str(row["window_id"]),
            int(row["reference_offset_in_read_order"]),
        )
    )

    readiness_rows: list[dict[str, Any]] = []
    for partition in PARTITIONS:
        for difference in ("extra", "missing"):
            counts = readiness.get((partition, difference), ReadinessCounts())
            readiness_rows.append(
                {
                    "partition": partition,
                    "difference": difference,
                    "cases": len(counts.cases),
                    "biological_differences": counts.differences,
                    "fit_eligible_differences": counts.fit_eligible_differences,
                    "phase_observations": counts.phase_observations,
                    "phase_reads": len(counts.phase_reads),
                    "exact_phase_windows": len(counts.phase_windows),
                }
            )
    return (
        detailed_differences,
        observation_rows,
        window_rows,
        candidate_rows,
        readiness_rows,
    )


def output_index(
    corpus: ResearchCorpus,
    evaluation_dir: Path,
    phase_dir: Path,
    hypotheses_dir: Path,
    plan: PartitionPlan,
    offsets: tuple[int, ...],
    paths: dict[str, Path],
    rows: dict[str, int],
) -> dict[str, Any]:
    return {
        "schema_version": VARIANT_PHASE_CONTEXT_SCHEMA_VERSION,
        "source_variant_profile_evaluation_sha256": file_sha256(
            evaluation_dir / "index.json"
        ),
        "source_corpus_sha256": file_sha256(corpus.index_path),
        "source_polyc_phase_sha256": file_sha256(phase_dir / "index.json"),
        "source_phase_hypotheses_sha256": file_sha256(hypotheses_dir / "index.json"),
        "signal_version": corpus.signal_version,
        "manifest_sha256": corpus.manifest_sha256,
        "reference_sha256": corpus.reference_sha256,
        "configuration_sha256": corpus.configuration_sha256,
        "partitions": plan.index_record(),
        "method": {
            "biological_differences": (
                "only variant-profile missing/extra rows; representation disagreements "
                "are excluded from phase-error attribution"
            ),
            "event_footprint": (
                "normalized source-event reference allele span; insertions retain their "
                "normalized anchor plus insertion_boundary_after_1based"
            ),
            "phase_scope": (
                "only exact post-tract observations present in the authoritative "
                "signal.validation_polyc_phase/v1 source"
            ),
            "window_membership": (
                "exact reconstructed membership from the authoritative profile-bearing "
                "phase window generator; interval containment is not used"
            ),
            "candidate_offsets": list(offsets),
            "candidate_selection": "none; complete source curve retained",
            "thresholds": "none",
            "holdout_policy": (
                "continuous difference/read/window/candidate context is exported only "
                "for fit-eligible development cases; other partitions expose counts only"
            ),
        },
        "differences_file": "differences.csv",
        "differences_sha256": file_sha256(paths["differences"]),
        "differences_rows": rows["differences"],
        "differences_columns": list(DIFFERENCE_COLUMNS_OUT),
        "observations_file": "observations.csv",
        "observations_sha256": file_sha256(paths["observations"]),
        "observations_rows": rows["observations"],
        "observations_columns": list(OBSERVATION_COLUMNS),
        "windows_file": "windows.csv",
        "windows_sha256": file_sha256(paths["windows"]),
        "windows_rows": rows["windows"],
        "windows_columns": list(WINDOW_COLUMNS),
        "candidates_file": "candidates.csv",
        "candidates_sha256": file_sha256(paths["candidates"]),
        "candidates_rows": rows["candidates"],
        "candidates_columns": list(CANDIDATE_COLUMNS),
        "readiness_file": "readiness.csv",
        "readiness_sha256": file_sha256(paths["readiness"]),
        "readiness_rows": rows["readiness"],
        "readiness_columns": list(READINESS_COLUMNS),
    }


def publish_variant_phase_context(
    evaluation_dir: Path,
    corpus_dir: Path,
    phase_dir: Path,
    hypotheses_dir: Path,
    output_dir: Path,
    plan: PartitionPlan,
) -> None:
    evaluation_dir = evaluation_dir.resolve()
    corpus_dir = corpus_dir.resolve()
    phase_dir = phase_dir.resolve()
    hypotheses_dir = hypotheses_dir.resolve()
    output_dir = output_dir.resolve()
    for label, path in (
        ("variant-profile evaluation", evaluation_dir),
        ("validation corpus", corpus_dir),
        ("poly-C phase", phase_dir),
        ("phase hypotheses", hypotheses_dir),
    ):
        if not path.is_dir():
            raise ValueError(f"{label} directory does not exist: {path}")
    validate_new_directory(
        output_dir,
        (evaluation_dir, corpus_dir, phase_dir, hypotheses_dir),
    )
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if not output_dir.parent.is_dir() or output_dir.parent.is_symlink():
        raise ValueError(
            f"output parent is not a regular directory: {output_dir.parent}"
        )

    evaluation_index, differences = load_evaluation(evaluation_dir)
    corpus = load_research_corpus(corpus_dir)
    (
        phase_index,
        _,
        offsets,
        groups,
        source_windows,
        candidates,
        generated_windows,
    ) = validate_source_pair(phase_dir, hypotheses_dir)
    validate_provenance(
        corpus,
        evaluation_index,
        phase_index,
    )
    reference = evaluation_index["reference"]
    reference_length = nonnegative_index_count(
        reference.get("length"), "reference.length"
    )
    if reference_length < 1:
        raise ValueError("reference.length must be positive")

    (
        difference_rows,
        observation_rows,
        window_rows,
        candidate_rows,
        readiness_rows,
    ) = build_rows(
        corpus,
        differences,
        reference_length,
        plan,
        groups,
        generated_windows,
        source_windows,
        candidates,
        offsets,
    )

    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        paths = {
            "differences": stage / "differences.csv",
            "observations": stage / "observations.csv",
            "windows": stage / "windows.csv",
            "candidates": stage / "candidates.csv",
            "readiness": stage / "readiness.csv",
        }
        write_rows(
            paths["differences"],
            difference_rows,
            DIFFERENCE_COLUMNS_OUT,
            "variant phase difference",
        )
        write_rows(
            paths["observations"],
            observation_rows,
            OBSERVATION_COLUMNS,
            "variant phase observation",
        )
        write_rows(
            paths["windows"],
            window_rows,
            WINDOW_COLUMNS,
            "variant phase window",
        )
        write_rows(
            paths["candidates"],
            candidate_rows,
            CANDIDATE_COLUMNS,
            "variant phase candidate",
        )
        write_rows(
            paths["readiness"],
            readiness_rows,
            READINESS_COLUMNS,
            "variant phase readiness",
        )
        write_json(
            stage / "index.json",
            output_index(
                corpus,
                evaluation_dir,
                phase_dir,
                hypotheses_dir,
                plan,
                offsets,
                paths,
                {
                    "differences": len(difference_rows),
                    "observations": len(observation_rows),
                    "windows": len(window_rows),
                    "candidates": len(candidate_rows),
                    "readiness": len(readiness_rows),
                },
            ),
        )
        sync_directory(stage)

        try:
            output_dir.mkdir()
        except FileExistsError as error:
            raise FileExistsError(
                "output directory appeared while variant phase context was running: "
                f"{output_dir}"
            ) from error
        try:
            for name in (
                "differences.csv",
                "observations.csv",
                "windows.csv",
                "candidates.csv",
                "readiness.csv",
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
    "DIFFERENCE_COLUMNS_OUT",
    "OBSERVATION_COLUMNS",
    "READINESS_COLUMNS",
    "WINDOW_COLUMNS",
    "VariantEvent",
    "event_footprint",
    "parse_event",
    "publish_variant_phase_context",
]
