"""Typed records and fixed columns for local validation research datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .model import RESEARCH_SCHEMA_VERSION

CASE_FIELDS = (
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
    "approval_record",
    "redistribution_status",
    "notes",
)

READ_FIELDS = (
    "trace_sha256",
    "pcr_replicate_id",
    "sequencing_run_id",
    "instrument_id",
    "amplicon_id",
    "declared_direction",
    "artifact_tags",
)

LOCUS_FIELDS = (
    "schema_version",
    "signal_version",
    "sample_id",
    "reference_sha256",
    "configuration_sha256",
    "position_1based",
    "reference_base",
    "reads",
    "forward_reads",
    "reverse_reads",
    "reference_reads",
    "alternate_reads",
    "unresolved_reads",
    "deletion_reads",
    "profile_reads",
    "profile_forward_reads",
    "profile_reverse_reads",
    "contributors",
    "forward_contributors",
    "reverse_contributors",
    "mean_a",
    "mean_c",
    "mean_g",
    "mean_t",
    "within_profile_impurity",
    "between_profile_dispersion",
    "total_profile_heterogeneity",
    "forward_within_profile_impurity",
    "forward_between_profile_dispersion",
    "forward_total_profile_heterogeneity",
    "reverse_within_profile_impurity",
    "reverse_between_profile_dispersion",
    "reverse_total_profile_heterogeneity",
    "directional_profile_distance",
    "noisy_observations",
    "missing_profile_observations",
    "deletion_observations",
    "observations",
)

OBSERVATION_FIELDS = (
    "read_sha256",
    "orientation",
    "state",
    "aligned_base",
    "quality",
    "call_index_0based",
    "source_primary",
    "source_ambiguity",
    "ploc_0based",
    "window_start_0based",
    "window_end_0based_exclusive",
    "primary_peak_position_0based",
    "primary_peak_offset_from_ploc",
    "event_position_0based",
    "event_offset_from_ploc",
    "event_offset_from_primary_peak",
    "channel_peak_positions_acgt_reference",
    "channel_peak_heights_acgt_reference",
    "channel_peak_sources_acgt_reference",
    "primary_peak_heights_acgt_reference",
    "corrected_amplitudes_acgt_reference",
    "snrs_acgt_reference",
    "profile_acgt_reference",
    "in_noisy_region",
)

METRICS = (
    "within_profile_impurity",
    "between_profile_dispersion",
    "total_profile_heterogeneity",
    "directional_profile_distance",
)

LOCUS_TABLE_COLUMNS = (
    *CASE_FIELDS,
    "is_truth_locus",
    *LOCUS_FIELDS[:-1],
)

OBSERVATION_TABLE_COLUMNS = (
    *CASE_FIELDS,
    "is_truth_locus",
    "position_1based",
    "reference_base",
    "read_sha256",
    "pcr_replicate_id",
    "sequencing_run_id",
    "instrument_id",
    "amplicon_id",
    "declared_direction",
    "artifact_tags",
    "orientation",
    "state",
    "aligned_base",
    "quality",
    "call_index_0based",
    "source_primary",
    "source_ambiguity",
    "ploc_0based",
    "window_start_0based",
    "window_end_0based_exclusive",
    "primary_peak_position_0based",
    "primary_peak_offset_from_ploc",
    "event_position_0based",
    "event_offset_from_ploc",
    "event_offset_from_primary_peak",
    "channel_peak_position_a",
    "channel_peak_position_c",
    "channel_peak_position_g",
    "channel_peak_position_t",
    "channel_peak_height_a",
    "channel_peak_height_c",
    "channel_peak_height_g",
    "channel_peak_height_t",
    "channel_peak_source_a",
    "channel_peak_source_c",
    "channel_peak_source_g",
    "channel_peak_source_t",
    "primary_peak_height_a",
    "primary_peak_height_c",
    "primary_peak_height_g",
    "primary_peak_height_t",
    "corrected_amplitude_a",
    "corrected_amplitude_c",
    "corrected_amplitude_g",
    "corrected_amplitude_t",
    "snr_a",
    "snr_c",
    "snr_g",
    "snr_t",
    "profile_a",
    "profile_c",
    "profile_g",
    "profile_t",
    "in_noisy_region",
)


@dataclass(frozen=True)
class ResearchCase:
    metadata: dict[str, Any]
    measurement_file: Path
    loci: int
    reads: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class ResearchCorpus:
    index_path: Path
    signal_version: str
    manifest_sha256: str
    reference_sha256: str
    configuration_sha256: str
    cases: list[ResearchCase]


__all__ = [
    "CASE_FIELDS",
    "LOCUS_FIELDS",
    "LOCUS_TABLE_COLUMNS",
    "METRICS",
    "OBSERVATION_FIELDS",
    "OBSERVATION_TABLE_COLUMNS",
    "READ_FIELDS",
    "RESEARCH_SCHEMA_VERSION",
    "ResearchCase",
    "ResearchCorpus",
]
