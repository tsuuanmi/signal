"""Prepare development-only phase interpretation research tables."""

from __future__ import annotations

import csv
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO

from .filesystem import file_sha256, sync_directory, validate_new_directory, write_json
from .model import PHASE_INTERPRETATION_DATASET_SCHEMA_VERSION
from .phase_artifact import (
    CandidateRecord,
    WindowRecord,
    load_source,
    production_v1_parameters,
    validate_source,
)
from .phase_hypotheses import HYPOTHESIS_COLUMNS
from .research_loader import iter_research_rows, load_research_corpus
from .research_model import ResearchCase, ResearchCorpus

PARTITIONS = ("development", "holdout", "excluded", "unassigned")

DEVELOPMENT_WINDOW_COLUMNS = (
    "window_id",
    "validation_case_id",
    "source_group_id",
    "specimen_group_id",
    "truth_class",
    "truth_method",
    "truth_locus",
    "truth_reference",
    "truth_alternate",
    "known_mixture_fraction",
    "include_in_threshold_fit",
    "holdout_group",
    "read_sha256",
    "pcr_replicate_id",
    "sequencing_run_id",
    "instrument_id",
    "amplicon_id",
    "declared_direction",
    "artifact_tags",
    "orientation",
    "tract_id",
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

READINESS_COLUMNS = (
    "partition",
    "holdout_group",
    "include_in_threshold_fit",
    "truth_class",
    "tract_id",
    "orientation",
    "amplicon_id",
    "interrupt_aligned_base",
    "cases",
    "source_groups",
    "specimen_groups",
    "pcr_replicates",
    "sequencing_runs",
    "instruments",
    "reads",
    "read_tracts",
    "windows",
    "candidates",
)


@dataclass(frozen=True)
class PartitionPlan:
    development: tuple[str, ...]
    holdout: tuple[str, ...]
    excluded: tuple[str, ...] = ()
    unassigned: tuple[str, ...] = ()

    def mapping(self) -> dict[str, str]:
        if not self.development:
            raise ValueError("at least one development holdout_group must be declared")
        if not self.holdout:
            raise ValueError("at least one holdout holdout_group must be declared")

        mapping: dict[str, str] = {}
        for partition, groups in (
            ("development", self.development),
            ("holdout", self.holdout),
            ("excluded", self.excluded),
            ("unassigned", self.unassigned),
        ):
            seen: set[str] = set()
            for group in groups:
                if not group:
                    raise ValueError(f"{partition} holdout_group must be non-empty")
                if group in seen:
                    raise ValueError(
                        f"duplicate {partition} holdout_group declaration: {group!r}"
                    )
                seen.add(group)
                previous = mapping.setdefault(group, partition)
                if previous != partition:
                    raise ValueError(
                        f"holdout_group {group!r} is declared as both "
                        f"{previous} and {partition}"
                    )
        return mapping

    def index_record(self) -> dict[str, list[str]]:
        return {
            "development": list(self.development),
            "holdout": list(self.holdout),
            "excluded": list(self.excluded),
            "unassigned": list(self.unassigned),
        }


@dataclass
class CountAccumulator:
    cases: set[str] = field(default_factory=set)
    fit_cases: set[str] = field(default_factory=set)
    source_groups: set[str] = field(default_factory=set)
    specimen_groups: set[str] = field(default_factory=set)
    pcr_replicates: set[tuple[str, str]] = field(default_factory=set)
    sequencing_runs: set[str] = field(default_factory=set)
    instruments: set[str] = field(default_factory=set)
    reads: set[str] = field(default_factory=set)
    phase_reads: set[str] = field(default_factory=set)
    read_tracts: set[tuple[str, str]] = field(default_factory=set)
    windows: int = 0
    candidates: int = 0

    def add_case(self, case: ResearchCase) -> None:
        metadata = case.metadata
        case_id = str(metadata["validation_case_id"])
        self.cases.add(case_id)
        if metadata["include_in_threshold_fit"] is True:
            self.fit_cases.add(case_id)
        source_group = str(metadata["source_group_id"])
        self.source_groups.add(source_group)
        specimen = metadata["specimen_group_id"]
        if specimen is not None:
            self.specimen_groups.add(str(specimen))

        for read_sha256, read in case.reads.items():
            self.reads.add(read_sha256)
            pcr_replicate = read["pcr_replicate_id"]
            if pcr_replicate is not None:
                self.pcr_replicates.add((source_group, str(pcr_replicate)))
            sequencing_run = read["sequencing_run_id"]
            if sequencing_run is not None:
                self.sequencing_runs.add(str(sequencing_run))
            instrument = read["instrument_id"]
            if instrument is not None:
                self.instruments.add(str(instrument))

    def add_window(self, window: WindowRecord, candidate_count: int) -> None:
        self.phase_reads.add(window.read_sha256)
        self.read_tracts.add((window.read_sha256, window.tract_id))
        self.windows += 1
        self.candidates += candidate_count

    def result(self) -> dict[str, int]:
        return {
            "cases": len(self.cases),
            "fit_cases": len(self.fit_cases),
            "source_groups": len(self.source_groups),
            "specimen_groups": len(self.specimen_groups),
            "pcr_replicates": len(self.pcr_replicates),
            "sequencing_runs": len(self.sequencing_runs),
            "instruments": len(self.instruments),
            "reads": len(self.reads),
            "phase_reads": len(self.phase_reads),
            "read_tracts": len(self.read_tracts),
            "windows": self.windows,
            "candidates": self.candidates,
        }


@dataclass
class ReadinessAccumulator:
    cases: set[str] = field(default_factory=set)
    source_groups: set[str] = field(default_factory=set)
    specimen_groups: set[str] = field(default_factory=set)
    pcr_replicates: set[tuple[str, str]] = field(default_factory=set)
    sequencing_runs: set[str] = field(default_factory=set)
    instruments: set[str] = field(default_factory=set)
    reads: set[str] = field(default_factory=set)
    read_tracts: set[tuple[str, str]] = field(default_factory=set)
    windows: int = 0
    candidates: int = 0

    def add(
        self,
        case: ResearchCase,
        read_sha256: str,
        window: WindowRecord,
        candidate_count: int,
    ) -> None:
        metadata = case.metadata
        read = case.reads[read_sha256]
        self.cases.add(str(metadata["validation_case_id"]))
        source_group = str(metadata["source_group_id"])
        self.source_groups.add(source_group)
        specimen = metadata["specimen_group_id"]
        if specimen is not None:
            self.specimen_groups.add(str(specimen))
        pcr_replicate = read["pcr_replicate_id"]
        if pcr_replicate is not None:
            self.pcr_replicates.add((source_group, str(pcr_replicate)))
        sequencing_run = read["sequencing_run_id"]
        if sequencing_run is not None:
            self.sequencing_runs.add(str(sequencing_run))
        instrument = read["instrument_id"]
        if instrument is not None:
            self.instruments.add(str(instrument))
        self.reads.add(read_sha256)
        self.read_tracts.add((read_sha256, window.tract_id))
        self.windows += 1
        self.candidates += candidate_count

    def counts(self) -> tuple[int, ...]:
        return (
            len(self.cases),
            len(self.source_groups),
            len(self.specimen_groups),
            len(self.pcr_replicates),
            len(self.sequencing_runs),
            len(self.instruments),
            len(self.reads),
            len(self.read_tracts),
            self.windows,
            self.candidates,
        )


ReadinessKey = tuple[str, str, bool, str, str, str, str, str]


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


def case_map(corpus: ResearchCorpus) -> dict[str, ResearchCase]:
    cases: dict[str, ResearchCase] = {}
    for case in corpus.cases:
        case_id = str(case.metadata["validation_case_id"])
        if case_id in cases:
            raise ValueError(f"duplicate validation_case_id in corpus: {case_id}")
        cases[case_id] = case
    return cases


def selected_orientations(corpus: ResearchCorpus) -> dict[tuple[str, str], str]:
    expected = {
        (str(case.metadata["validation_case_id"]), read_sha256)
        for case in corpus.cases
        for read_sha256 in case.reads
    }
    orientations: dict[tuple[str, str], str] = {}

    for _, observations in iter_research_rows(corpus):
        for observation in observations:
            case_id = str(observation["validation_case_id"])
            read_sha256 = str(observation["read_sha256"])
            orientation = str(observation["orientation"])
            if orientation not in {"forward", "reverse"}:
                raise ValueError(
                    f"{case_id}/{read_sha256}: selected orientation is invalid"
                )
            key = (case_id, read_sha256)
            previous = orientations.setdefault(key, orientation)
            if previous != orientation:
                raise ValueError(
                    f"{case_id}/{read_sha256}: selected orientation changes across loci"
                )

    missing = sorted(expected - set(orientations))
    if missing:
        case_id, read_sha256 = missing[0]
        raise ValueError(
            f"{case_id}/{read_sha256}: no selected orientation in corpus measurements"
        )
    extra = sorted(set(orientations) - expected)
    if extra:
        case_id, read_sha256 = extra[0]
        raise ValueError(
            f"{case_id}/{read_sha256}: measurement orientation references unknown read"
        )
    return orientations


def validate_provenance(
    corpus: ResearchCorpus,
    source_index: dict[str, Any],
) -> None:
    expected_corpus_sha256 = file_sha256(corpus.index_path)
    checks = (
        (
            "source corpus SHA-256",
            source_index["source_corpus_sha256"],
            expected_corpus_sha256,
        ),
        ("manifest SHA-256", source_index["manifest_sha256"], corpus.manifest_sha256),
        ("Signal version", source_index["signal_version"], corpus.signal_version),
        (
            "reference SHA-256",
            source_index["reference_sha256"],
            corpus.reference_sha256,
        ),
        (
            "configuration SHA-256",
            source_index["configuration_sha256"],
            corpus.configuration_sha256,
        ),
    )
    for label, observed, expected in checks:
        if observed != expected:
            raise ValueError(f"phase hypotheses {label} differs from validation corpus")


def partition_for(
    holdout_group: str,
    mapping: dict[str, str],
) -> str:
    partition = mapping.get(holdout_group)
    if partition is None:
        raise ValueError(
            f"holdout_group {holdout_group!r} has no declared study partition"
        )
    return partition


def validate_declared_groups(
    corpus: ResearchCorpus,
    mapping: dict[str, str],
) -> None:
    for case in corpus.cases:
        group = str(case.metadata["holdout_group"])
        partition_for(group, mapping)


def development_window_row(
    case: ResearchCase,
    window: WindowRecord,
) -> dict[str, Any]:
    metadata = case.metadata
    read = case.reads[window.read_sha256]
    return {
        "window_id": window.window_id,
        "validation_case_id": metadata["validation_case_id"],
        "source_group_id": metadata["source_group_id"],
        "specimen_group_id": metadata["specimen_group_id"],
        "truth_class": metadata["truth_class"],
        "truth_method": metadata["truth_method"],
        "truth_locus": metadata["truth_locus"],
        "truth_reference": metadata["truth_reference"],
        "truth_alternate": metadata["truth_alternate"],
        "known_mixture_fraction": metadata["known_mixture_fraction"],
        "include_in_threshold_fit": metadata["include_in_threshold_fit"],
        "holdout_group": metadata["holdout_group"],
        "read_sha256": window.read_sha256,
        "pcr_replicate_id": read["pcr_replicate_id"],
        "sequencing_run_id": read["sequencing_run_id"],
        "instrument_id": read["instrument_id"],
        "amplicon_id": read["amplicon_id"],
        "declared_direction": read["declared_direction"],
        "artifact_tags": ";".join(read["artifact_tags"]),
        "orientation": window.orientation,
        "tract_id": window.tract_id,
        "interrupt_aligned_base": window.interrupt_aligned_base,
        "start_distance_after_tract": window.start_distance,
        "end_distance_after_tract": window.end_distance,
        "start_call_index_0based": window.start_call_index,
        "end_call_index_0based": window.end_call_index,
        "profile_observations": window.profile_observations,
        "noisy_observations": window.noisy_observations,
        "mean_profile_impurity": window.mean_profile_impurity,
        "mean_zero_reference_mass": window.mean_zero_reference_mass,
    }


def candidate_row(candidate: CandidateRecord) -> dict[str, Any]:
    return {
        "window_id": candidate.window_id,
        "reference_offset_in_read_order": candidate.offset,
        "informative_positions": candidate.informative_positions,
        "mean_zero_reference_mass": candidate.zero_mass,
        "mean_shifted_reference_mass": candidate.shifted_mass,
        "mean_residual_mass": candidate.residual_mass,
    }


def readiness_key(
    partition: str,
    case: ResearchCase,
    window: WindowRecord,
) -> ReadinessKey:
    metadata = case.metadata
    return (
        partition,
        str(metadata["holdout_group"]),
        bool(metadata["include_in_threshold_fit"]),
        str(metadata["truth_class"]),
        window.tract_id,
        window.orientation,
        window.amplicon_id,
        window.interrupt_aligned_base,
    )


def readiness_rows(
    accumulators: dict[ReadinessKey, ReadinessAccumulator],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in sorted(accumulators):
        (
            partition,
            holdout_group,
            include_in_threshold_fit,
            truth_class,
            tract_id,
            orientation,
            amplicon_id,
            interrupt_aligned_base,
        ) = key
        counts = accumulators[key].counts()
        rows.append(
            {
                "partition": partition,
                "holdout_group": holdout_group,
                "include_in_threshold_fit": include_in_threshold_fit,
                "truth_class": truth_class,
                "tract_id": tract_id,
                "orientation": orientation,
                "amplicon_id": amplicon_id,
                "interrupt_aligned_base": interrupt_aligned_base,
                "cases": counts[0],
                "source_groups": counts[1],
                "specimen_groups": counts[2],
                "pcr_replicates": counts[3],
                "sequencing_runs": counts[4],
                "instruments": counts[5],
                "reads": counts[6],
                "read_tracts": counts[7],
                "windows": counts[8],
                "candidates": counts[9],
            }
        )
    return rows


def build_rows(
    corpus: ResearchCorpus,
    windows: dict[str, WindowRecord],
    candidates: dict[tuple[str, int], CandidateRecord],
    offsets: tuple[int, ...],
    plan: PartitionPlan,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, dict[str, int]],
]:
    mapping = plan.mapping()
    validate_declared_groups(corpus, mapping)
    cases = case_map(corpus)
    orientations = selected_orientations(corpus)

    partition_counts = {partition: CountAccumulator() for partition in PARTITIONS}
    for case in corpus.cases:
        partition = partition_for(str(case.metadata["holdout_group"]), mapping)
        partition_counts[partition].add_case(case)

    development_windows: list[dict[str, Any]] = []
    development_candidates: list[dict[str, Any]] = []
    readiness: dict[ReadinessKey, ReadinessAccumulator] = {}

    ordered_windows = sorted(
        windows.values(),
        key=lambda window: (
            window.validation_case_id,
            window.read_sha256,
            window.tract_id,
            window.start_distance,
            window.window_id,
        ),
    )
    for window in ordered_windows:
        case = cases.get(window.validation_case_id)
        if case is None:
            raise ValueError(
                f"{window.window_id}: phase window references unknown validation case"
            )
        read = case.reads.get(window.read_sha256)
        if read is None:
            raise ValueError(f"{window.window_id}: phase window references unknown read")

        expected_amplicon = "" if read["amplicon_id"] is None else str(read["amplicon_id"])
        if window.amplicon_id != expected_amplicon:
            raise ValueError(f"{window.window_id}: amplicon differs from corpus read metadata")

        expected_orientation = orientations[
            (window.validation_case_id, window.read_sha256)
        ]
        if window.orientation != expected_orientation:
            raise ValueError(
                f"{window.window_id}: selected orientation differs from corpus measurements"
            )

        partition = partition_for(str(case.metadata["holdout_group"]), mapping)
        curve = [candidates[(window.window_id, offset)] for offset in offsets]
        partition_counts[partition].add_window(window, len(curve))

        key = readiness_key(partition, case, window)
        readiness.setdefault(key, ReadinessAccumulator()).add(
            case,
            window.read_sha256,
            window,
            len(curve),
        )

        if partition != "development" or case.metadata["include_in_threshold_fit"] is not True:
            continue

        development_windows.append(development_window_row(case, window))
        development_candidates.extend(candidate_row(candidate) for candidate in curve)

    return (
        development_windows,
        development_candidates,
        readiness_rows(readiness),
        {
            partition: partition_counts[partition].result()
            for partition in PARTITIONS
        },
    )


def output_index(
    corpus: ResearchCorpus,
    source_dir: Path,
    source_index: dict[str, Any],
    plan: PartitionPlan,
    windows_path: Path,
    candidates_path: Path,
    readiness_path: Path,
    windows_count: int,
    candidates_count: int,
    readiness_count: int,
    partition_summary: dict[str, dict[str, int]],
) -> dict[str, Any]:
    return {
        "schema_version": PHASE_INTERPRETATION_DATASET_SCHEMA_VERSION,
        "source_corpus_sha256": file_sha256(corpus.index_path),
        "source_phase_hypotheses_sha256": file_sha256(source_dir / "index.json"),
        "source_polyc_phase_sha256": source_index["source_polyc_phase_sha256"],
        "signal_version": corpus.signal_version,
        "manifest_sha256": corpus.manifest_sha256,
        "reference_sha256": corpus.reference_sha256,
        "configuration_sha256": corpus.configuration_sha256,
        "partition_groups": plan.index_record(),
        "method": {
            "phase_method": "signal.polyc_phase/v1",
            "development_admission": (
                "declared development partition and include_in_threshold_fit=true"
            ),
            "holdout_phase_measurements_exported": False,
            "candidate_selection": "none; complete candidate curves retained",
            "interpretation": "none; no state, threshold, persistence, or recovery rule",
        },
        "partition_summary": partition_summary,
        "development_windows_file": "development-windows.csv",
        "development_windows_sha256": file_sha256(windows_path),
        "development_windows_rows": windows_count,
        "development_windows_columns": list(DEVELOPMENT_WINDOW_COLUMNS),
        "development_candidates_file": "development-candidates.csv",
        "development_candidates_sha256": file_sha256(candidates_path),
        "development_candidates_rows": candidates_count,
        "development_candidates_columns": list(HYPOTHESIS_COLUMNS),
        "readiness_file": "readiness.csv",
        "readiness_sha256": file_sha256(readiness_path),
        "readiness_rows": readiness_count,
        "readiness_columns": list(READINESS_COLUMNS),
    }


def build_staged_dataset(
    corpus: ResearchCorpus,
    source_dir: Path,
    source_index: dict[str, Any],
    windows: dict[str, WindowRecord],
    candidates: dict[tuple[str, int], CandidateRecord],
    offsets: tuple[int, ...],
    plan: PartitionPlan,
    stage: Path,
) -> None:
    (
        development_windows,
        development_candidates,
        readiness,
        partition_summary,
    ) = build_rows(
        corpus,
        windows,
        candidates,
        offsets,
        plan,
    )

    windows_path = stage / "development-windows.csv"
    candidates_path = stage / "development-candidates.csv"
    readiness_path = stage / "readiness.csv"
    write_rows(
        windows_path,
        development_windows,
        DEVELOPMENT_WINDOW_COLUMNS,
        "development window",
    )
    write_rows(
        candidates_path,
        development_candidates,
        HYPOTHESIS_COLUMNS,
        "development candidate",
    )
    write_rows(readiness_path, readiness, READINESS_COLUMNS, "readiness")

    write_json(
        stage / "index.json",
        output_index(
            corpus,
            source_dir,
            source_index,
            plan,
            windows_path,
            candidates_path,
            readiness_path,
            len(development_windows),
            len(development_candidates),
            len(readiness),
            partition_summary,
        ),
    )
    sync_directory(stage)


def publish_phase_interpretation_dataset(
    corpus_dir: Path,
    hypotheses_dir: Path,
    output_dir: Path,
    plan: PartitionPlan,
) -> None:
    corpus_dir = corpus_dir.resolve()
    hypotheses_dir = hypotheses_dir.resolve()
    output_dir = output_dir.resolve()
    if not corpus_dir.is_dir():
        raise ValueError(f"corpus directory does not exist: {corpus_dir}")
    if not hypotheses_dir.is_dir():
        raise ValueError(f"phase-hypothesis directory does not exist: {hypotheses_dir}")

    validate_new_directory(output_dir, (corpus_dir, hypotheses_dir))
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if not output_dir.parent.is_dir() or output_dir.parent.is_symlink():
        raise ValueError(
            f"output parent is not a regular directory: {output_dir.parent}"
        )

    corpus = load_research_corpus(corpus_dir)
    source_index, offsets = validate_source(hypotheses_dir)
    production_v1_parameters(source_index["method"])
    validate_provenance(corpus, source_index)
    windows, candidates = load_source(hypotheses_dir, source_index, offsets)

    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        build_staged_dataset(
            corpus,
            hypotheses_dir,
            source_index,
            windows,
            candidates,
            offsets,
            plan,
            stage,
        )
        try:
            output_dir.mkdir()
        except FileExistsError as error:
            raise FileExistsError(
                "output directory appeared while phase interpretation dataset "
                f"was being prepared: {output_dir}"
            ) from error

        try:
            for name in (
                "development-windows.csv",
                "development-candidates.csv",
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
    "DEVELOPMENT_WINDOW_COLUMNS",
    "PartitionPlan",
    "READINESS_COLUMNS",
    "publish_phase_interpretation_dataset",
]
