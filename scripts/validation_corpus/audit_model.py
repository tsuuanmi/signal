"""Typed audit records and fixed output columns for validation review strata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .model import AUDIT_SCHEMA_VERSION

READ_AUDIT_COLUMNS = (
    "validation_case_id",
    "read_sha256",
    "sequencing_run_id",
    "amplicon_id",
    "declared_direction",
    "inferred_orientation",
    "calls",
    "profiled_loci",
    "noisy_calls",
    "noise_rate",
    "trim_start_0based",
    "trim_end_0based_exclusive",
    "retained",
    "retained_fraction",
    "callable_columns",
    "callable_identity",
    "mismatches",
    "gap_opens",
    "excluded_variant_candidates",
    "stratum_key",
    "stratum_n",
    "identity_p05",
    "noise_p95",
    "retained_fraction_p05",
    "callable_columns_p05",
    "alignment_challenge",
    "high_noise",
    "aggressive_trim",
    "short_coverage",
    "orientation_disagreement",
    "unbenchmarked_stratum",
    "audit_flags",
)

LOCUS_AUDIT_COLUMNS = (
    "validation_case_id",
    "position_1based",
    "reference_base",
    "reads",
    "reference_reads",
    "alternate_reads",
    "contributors",
    "forward_contributors",
    "reverse_contributors",
    "within_profile_impurity",
    "between_profile_dispersion",
    "total_profile_heterogeneity",
    "directional_profile_distance",
    "alternate_observations",
    "alternate_forward_observations",
    "alternate_reverse_observations",
    "alternate_noisy_observations",
    "alternate_near_read_edge_observations",
    "minimum_alternate_edge_distance_calls",
    "cross_orientation_alternate",
    "edge_discordance",
    "audit_flags",
)

CASE_AUDIT_COLUMNS = (
    "validation_case_id",
    "source_group_id",
    "specimen_group_id",
    "reads",
    "loci",
    "alternate_loci",
    "mixed_loci",
    "edge_discordance_loci",
    "noisy_loci",
    "bidirectional_loci",
    "p95_within_profile_impurity",
    "p95_between_profile_dispersion",
    "p95_total_profile_heterogeneity",
    "p95_directional_profile_distance",
    "minimum_callable_identity",
    "maximum_noise_rate",
    "minimum_retained_fraction",
    "minimum_callable_columns",
    "alignment_challenge_reads",
    "high_noise_reads",
    "aggressive_trim_reads",
    "short_coverage_reads",
    "orientation_disagreement_reads",
    "unbenchmarked_reads",
    "short_coverage_cluster",
    "geometry_challenge",
    "audit_flags",
)

READ_FLAG_ORDER = (
    "alignment_challenge",
    "high_noise",
    "aggressive_trim",
    "short_coverage",
    "orientation_disagreement",
    "unbenchmarked_stratum",
)

CASE_FLAG_ORDER = (
    "alignment_challenge",
    "high_noise",
    "aggressive_trim",
    "short_coverage_cluster",
    "geometry_challenge",
    "edge_discordance",
    "orientation_disagreement",
    "unbenchmarked_stratum",
)

MINIMUM_STRATUM_READS = 20
LOWER_AUDIT_QUANTILE = 0.05
UPPER_AUDIT_QUANTILE = 0.95
EDGE_DISTANCE_CALLS = 10


@dataclass(frozen=True)
class RawReadAudit:
    validation_case_id: str
    read_sha256: str
    sequencing_run_id: str | None
    amplicon_id: str | None
    declared_direction: str | None
    inferred_orientation: str
    calls: int
    profiled_loci: int
    noisy_calls: int
    trim_start_0based: int
    trim_end_0based_exclusive: int
    retained: int
    retained_fraction: float
    callable_columns: int
    callable_identity: float
    mismatches: int
    gap_opens: int
    excluded_variant_candidates: int

    @property
    def noise_rate(self) -> float:
        if self.calls <= 0:
            return 0.0
        return self.noisy_calls / self.calls

    @property
    def stratum_key(self) -> tuple[str, str] | None:
        if self.amplicon_id is None or self.declared_direction is None:
            return None
        return self.amplicon_id, self.declared_direction


@dataclass(frozen=True)
class AuditBoundary:
    n: int
    identity_p05: float
    noise_p95: float
    retained_fraction_p05: float
    callable_columns_p05: float


__all__ = [
    "AUDIT_SCHEMA_VERSION",
    "AuditBoundary",
    "CASE_AUDIT_COLUMNS",
    "CASE_FLAG_ORDER",
    "EDGE_DISTANCE_CALLS",
    "LOCUS_AUDIT_COLUMNS",
    "LOWER_AUDIT_QUANTILE",
    "MINIMUM_STRATUM_READS",
    "READ_AUDIT_COLUMNS",
    "READ_FLAG_ORDER",
    "RawReadAudit",
    "UPPER_AUDIT_QUANTILE",
]
