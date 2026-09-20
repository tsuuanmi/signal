"""Typed local validation-corpus records and schema constants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA_VERSION = "signal.validation_manifest/v1"
CORPUS_SCHEMA_VERSION = "signal.validation_corpus/v1"
MEASUREMENT_SCHEMA_VERSION = "signal.validation_locus/v2"
RESEARCH_SCHEMA_VERSION = "signal.validation_research/v1"
AUDIT_SCHEMA_VERSION = "signal.validation_audit/v1"
CURATION_QUEUE_SCHEMA_VERSION = "signal.validation_curation_queue/v1"
POLYC_PHASE_SCHEMA_VERSION = "signal.validation_polyc_phase/v1"
POLYC_ORIENTATION_CONTROL_SCHEMA_VERSION = (
    "signal.validation_polyc_orientation_controls/v2"
)
PHASE_HYPOTHESIS_SCHEMA_VERSION = "signal.validation_phase_hypotheses/v1"
PHASE_CHARACTERIZATION_SCHEMA_VERSION = "signal.validation_phase_characterization/v1"
PHASE_SENSITIVITY_SCHEMA_VERSION = "signal.validation_phase_sensitivity/v1"
PHASE_EXPLAINABILITY_SCHEMA_VERSION = "signal.validation_phase_explainability/v1"
PHASE_RECURRENT_LOCUS_SCHEMA_VERSION = "signal.validation_phase_recurrent_loci/v1"
PHASE_INTERPRETATION_DATASET_SCHEMA_VERSION = (
    "signal.validation_phase_interpretation_dataset/v1"
)
REVIEWER_VARIANT_GROUND_TRUTH_SCHEMA_VERSION = "signal.reviewer_variant_ground_truth/v1"
VARIANT_PROFILE_EVALUATION_SCHEMA_VERSION = (
    "signal.validation_variant_profile_evaluation/v2"
)
VARIANT_PHASE_CONTEXT_SCHEMA_VERSION = "signal.validation_variant_phase_context/v1"
PHASE_ERROR_CHARACTERIZATION_SCHEMA_VERSION = (
    "signal.validation_phase_error_characterization/v1"
)

MANIFEST_COLUMNS = (
    "validation_case_id",
    "trace_path",
    "trace_sha256",
    "source_group_id",
    "specimen_group_id",
    "pcr_replicate_id",
    "sequencing_run_id",
    "instrument_id",
    "amplicon_id",
    "declared_direction",
    "truth_class",
    "truth_method",
    "truth_locus",
    "truth_reference",
    "truth_alternate",
    "known_mixture_fraction",
    "artifact_tags",
    "include_in_threshold_fit",
    "holdout_group",
    "approval_record",
    "redistribution_status",
    "notes",
)

CASE_COLUMNS = (
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
    "approval_record",
    "redistribution_status",
    "notes",
)


@dataclass(frozen=True)
class TraceRecord:
    path: Path
    trace_sha256: str
    pcr_replicate_id: str | None
    sequencing_run_id: str | None
    instrument_id: str | None
    amplicon_id: str | None
    declared_direction: str | None
    artifact_tags: tuple[str, ...]

    def index_record(self) -> dict[str, Any]:
        return {
            "trace_sha256": self.trace_sha256,
            "pcr_replicate_id": self.pcr_replicate_id,
            "sequencing_run_id": self.sequencing_run_id,
            "instrument_id": self.instrument_id,
            "amplicon_id": self.amplicon_id,
            "declared_direction": self.declared_direction,
            "artifact_tags": list(self.artifact_tags),
        }


@dataclass(frozen=True)
class CaseMetadata:
    validation_case_id: str
    source_group_id: str
    specimen_group_id: str | None
    truth_class: str
    truth_method: str
    truth_locus: int | None
    truth_reference: str | None
    truth_alternate: str | None
    known_mixture_fraction: float | None
    include_in_threshold_fit: bool
    holdout_group: str
    approval_record: str
    redistribution_status: str
    notes: str | None

    def index_record(self) -> dict[str, Any]:
        return {
            "validation_case_id": self.validation_case_id,
            "source_group_id": self.source_group_id,
            "specimen_group_id": self.specimen_group_id,
            "truth_class": self.truth_class,
            "truth_method": self.truth_method,
            "truth_locus": self.truth_locus,
            "truth_reference": self.truth_reference,
            "truth_alternate": self.truth_alternate,
            "known_mixture_fraction": self.known_mixture_fraction,
            "include_in_threshold_fit": self.include_in_threshold_fit,
            "holdout_group": self.holdout_group,
            "approval_record": self.approval_record,
            "redistribution_status": self.redistribution_status,
            "notes": self.notes,
        }


@dataclass
class ValidationCase:
    metadata: CaseMetadata
    traces: list[TraceRecord]


@dataclass(frozen=True)
class MeasurementSummary:
    schema_version: str
    signal_version: str
    reference_sha256: str
    configuration_sha256: str
    loci: int


@dataclass(frozen=True)
class ValidatedMeasurements:
    summary: MeasurementSummary
    rows: list[dict[str, Any]]
