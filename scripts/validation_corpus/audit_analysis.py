"""Derive deterministic observational audit strata from validation research data."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .model import AUDIT_SCHEMA_VERSION
from .research_model import LOCUS_TABLE_COLUMNS, OBSERVATION_TABLE_COLUMNS
from .research_statistics import nearest_rank

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
    "alignment_challenge",
    "high_noise",
    "aggressive_trim",
    "short_coverage",
    "edge_discordance",
    "orientation_disagreement",
    "unbenchmarked_stratum",
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
    "short_coverage",
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
        return self.noisy_calls / self.calls if self.calls else 0.0

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


@dataclass
class CaseGeometry:
    source_group_id: str
    specimen_group_id: str
    loci: int = 0
    alternate_loci: int = 0
    mixed_loci: int = 0
    noisy_loci: int = 0
    bidirectional_loci: int = 0
    within: list[float] = field(default_factory=list)
    between: list[float] = field(default_factory=list)
    total: list[float] = field(default_factory=list)
    directional: list[float] = field(default_factory=list)


@dataclass
class MixedLocus:
    validation_case_id: str
    position_1based: int
    reference_base: str
    reads: int
    reference_reads: int
    alternate_reads: int
    contributors: int
    forward_contributors: int
    reverse_contributors: int
    within_profile_impurity: float | None
    between_profile_dispersion: float | None
    total_profile_heterogeneity: float | None
    directional_profile_distance: float | None
    alternate_observations: int = 0
    alternate_forward_observations: int = 0
    alternate_reverse_observations: int = 0
    alternate_noisy_observations: int = 0
    alternate_near_read_edge_observations: int = 0
    minimum_alternate_edge_distance_calls: int | None = None


def csv_int(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"{label} must be an integer, got {value!r}") from error


def csv_float(value: str, label: str) -> float | None:
    if value == "":
        return None
    try:
        return float(value)
    except ValueError as error:
        raise ValueError(f"{label} must be numeric or empty, got {value!r}") from error


def csv_bool(value: str, label: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"{label} must be true or false, got {value!r}")


def validate_header(
    reader: csv.DictReader[str],
    expected: tuple[str, ...],
    label: str,
) -> None:
    if reader.fieldnames is None or tuple(reader.fieldnames) != expected:
        raise ValueError(f"{label} has unexpected columns")


def boundary_for(records: list[RawReadAudit]) -> AuditBoundary:
    return AuditBoundary(
        n=len(records),
        identity_p05=nearest_rank(
            [record.callable_identity for record in records],
            LOWER_AUDIT_QUANTILE,
        ),
        noise_p95=nearest_rank(
            [record.noise_rate for record in records],
            UPPER_AUDIT_QUANTILE,
        ),
        retained_fraction_p05=nearest_rank(
            [record.retained_fraction for record in records],
            LOWER_AUDIT_QUANTILE,
        ),
        callable_columns_p05=nearest_rank(
            [float(record.callable_columns) for record in records],
            LOWER_AUDIT_QUANTILE,
        ),
    )


def read_boundaries(
    records: list[RawReadAudit],
) -> dict[tuple[str, str], AuditBoundary]:
    groups: dict[tuple[str, str], list[RawReadAudit]] = defaultdict(list)
    for record in records:
        if record.stratum_key is not None:
            groups[record.stratum_key].append(record)
    return {key: boundary_for(group) for key, group in sorted(groups.items())}


def flags_text(flags: dict[str, bool], order: tuple[str, ...]) -> str:
    return ";".join(name for name in order if flags[name])


def read_audit_rows(
    records: list[RawReadAudit],
    boundaries: dict[tuple[str, str], AuditBoundary],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        key = record.stratum_key
        boundary = boundaries.get(key) if key is not None else None
        benchmarked = boundary is not None and boundary.n >= MINIMUM_STRATUM_READS
        flags = {
            "alignment_challenge": benchmarked
            and record.callable_identity <= boundary.identity_p05,
            "high_noise": benchmarked and record.noise_rate >= boundary.noise_p95,
            "aggressive_trim": benchmarked
            and record.retained_fraction <= boundary.retained_fraction_p05,
            "short_coverage": benchmarked
            and record.callable_columns <= boundary.callable_columns_p05,
            "orientation_disagreement": record.declared_direction is not None
            and record.declared_direction != record.inferred_orientation,
            "unbenchmarked_stratum": not benchmarked,
        }
        rows.append(
            {
                "validation_case_id": record.validation_case_id,
                "read_sha256": record.read_sha256,
                "sequencing_run_id": record.sequencing_run_id,
                "amplicon_id": record.amplicon_id,
                "declared_direction": record.declared_direction,
                "inferred_orientation": record.inferred_orientation,
                "calls": record.calls,
                "profiled_loci": record.profiled_loci,
                "noisy_calls": record.noisy_calls,
                "noise_rate": record.noise_rate,
                "trim_start_0based": record.trim_start_0based,
                "trim_end_0based_exclusive": record.trim_end_0based_exclusive,
                "retained": record.retained,
                "retained_fraction": record.retained_fraction,
                "callable_columns": record.callable_columns,
                "callable_identity": record.callable_identity,
                "mismatches": record.mismatches,
                "gap_opens": record.gap_opens,
                "excluded_variant_candidates": record.excluded_variant_candidates,
                "stratum_key": (
                    f"{key[0]}|{key[1]}" if key is not None else "unassigned"
                ),
                "stratum_n": boundary.n if boundary is not None else 0,
                "identity_p05": boundary.identity_p05 if benchmarked else None,
                "noise_p95": boundary.noise_p95 if benchmarked else None,
                "retained_fraction_p05": (
                    boundary.retained_fraction_p05 if benchmarked else None
                ),
                "callable_columns_p05": (
                    boundary.callable_columns_p05 if benchmarked else None
                ),
                **flags,
                "audit_flags": flags_text(flags, READ_FLAG_ORDER),
            }
        )
    return rows


def append_metric(target: list[float], value: str, label: str) -> None:
    parsed = csv_float(value, label)
    if parsed is not None:
        target.append(parsed)


def load_locus_context(
    loci_path: Path,
) -> tuple[dict[str, CaseGeometry], dict[tuple[str, int], MixedLocus]]:
    cases: dict[str, CaseGeometry] = {}
    mixed: dict[tuple[str, int], MixedLocus] = {}
    with loci_path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        validate_header(reader, LOCUS_TABLE_COLUMNS, str(loci_path))
        for line_number, row in enumerate(reader, 2):
            label = f"{loci_path}:{line_number}"
            case_id = row["validation_case_id"]
            source_group_id = row["source_group_id"]
            specimen_group_id = row["specimen_group_id"]
            geometry = cases.get(case_id)
            if geometry is None:
                geometry = CaseGeometry(source_group_id, specimen_group_id)
                cases[case_id] = geometry
            elif (
                geometry.source_group_id != source_group_id
                or geometry.specimen_group_id != specimen_group_id
            ):
                raise ValueError(f"{label}: case identity changes within loci.csv")

            reads = csv_int(row["reads"], f"{label}.reads")
            reference_reads = csv_int(
                row["reference_reads"], f"{label}.reference_reads"
            )
            alternate_reads = csv_int(
                row["alternate_reads"], f"{label}.alternate_reads"
            )
            forward_contributors = csv_int(
                row["forward_contributors"], f"{label}.forward_contributors"
            )
            reverse_contributors = csv_int(
                row["reverse_contributors"], f"{label}.reverse_contributors"
            )
            noisy_observations = csv_int(
                row["noisy_observations"], f"{label}.noisy_observations"
            )

            geometry.loci += 1
            geometry.alternate_loci += int(alternate_reads > 0)
            geometry.mixed_loci += int(reference_reads > 0 and alternate_reads > 0)
            geometry.noisy_loci += int(noisy_observations > 0)
            geometry.bidirectional_loci += int(
                forward_contributors > 0 and reverse_contributors > 0
            )
            append_metric(
                geometry.within,
                row["within_profile_impurity"],
                f"{label}.within_profile_impurity",
            )
            append_metric(
                geometry.between,
                row["between_profile_dispersion"],
                f"{label}.between_profile_dispersion",
            )
            append_metric(
                geometry.total,
                row["total_profile_heterogeneity"],
                f"{label}.total_profile_heterogeneity",
            )
            append_metric(
                geometry.directional,
                row["directional_profile_distance"],
                f"{label}.directional_profile_distance",
            )

            if reference_reads <= 0 or alternate_reads <= 0:
                continue
            position = csv_int(row["position_1based"], f"{label}.position_1based")
            key = (case_id, position)
            if key in mixed:
                raise ValueError(f"{label}: duplicate locus key {key}")
            mixed[key] = MixedLocus(
                validation_case_id=case_id,
                position_1based=position,
                reference_base=row["reference_base"],
                reads=reads,
                reference_reads=reference_reads,
                alternate_reads=alternate_reads,
                contributors=csv_int(row["contributors"], f"{label}.contributors"),
                forward_contributors=forward_contributors,
                reverse_contributors=reverse_contributors,
                within_profile_impurity=csv_float(
                    row["within_profile_impurity"],
                    f"{label}.within_profile_impurity",
                ),
                between_profile_dispersion=csv_float(
                    row["between_profile_dispersion"],
                    f"{label}.between_profile_dispersion",
                ),
                total_profile_heterogeneity=csv_float(
                    row["total_profile_heterogeneity"],
                    f"{label}.total_profile_heterogeneity",
                ),
                directional_profile_distance=csv_float(
                    row["directional_profile_distance"],
                    f"{label}.directional_profile_distance",
                ),
            )
    if not cases:
        raise ValueError(f"{loci_path}: no locus rows")
    return cases, mixed


def audit_mixed_observations(
    observations_path: Path,
    mixed: dict[tuple[str, int], MixedLocus],
    reads_by_sha256: dict[str, RawReadAudit],
) -> None:
    with observations_path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        validate_header(reader, OBSERVATION_TABLE_COLUMNS, str(observations_path))
        for line_number, row in enumerate(reader, 2):
            if row["state"] != "alternate":
                continue
            case_id = row["validation_case_id"]
            position = csv_int(
                row["position_1based"],
                f"{observations_path}:{line_number}.position_1based",
            )
            locus = mixed.get((case_id, position))
            if locus is None:
                continue

            read_sha256 = row["read_sha256"]
            read = reads_by_sha256.get(read_sha256)
            if read is None or read.validation_case_id != case_id:
                raise ValueError(
                    f"{observations_path}:{line_number}: alternate observation "
                    "references an unknown audit read"
                )
            call_index = csv_int(
                row["call_index_0based"],
                f"{observations_path}:{line_number}.call_index_0based",
            )
            if not (
                read.trim_start_0based <= call_index < read.trim_end_0based_exclusive
            ):
                raise ValueError(
                    f"{observations_path}:{line_number}: alternate call index "
                    "lies outside retained trim bounds"
                )
            edge_distance = min(
                call_index - read.trim_start_0based,
                read.trim_end_0based_exclusive - 1 - call_index,
            )
            orientation = row["orientation"]
            if orientation not in {"forward", "reverse"}:
                raise ValueError(
                    f"{observations_path}:{line_number}: invalid orientation "
                    f"{orientation!r}"
                )

            locus.alternate_observations += 1
            locus.alternate_forward_observations += int(orientation == "forward")
            locus.alternate_reverse_observations += int(orientation == "reverse")
            locus.alternate_noisy_observations += int(
                csv_bool(
                    row["in_noisy_region"],
                    f"{observations_path}:{line_number}.in_noisy_region",
                )
            )
            locus.alternate_near_read_edge_observations += int(
                edge_distance <= EDGE_DISTANCE_CALLS
            )
            if (
                locus.minimum_alternate_edge_distance_calls is None
                or edge_distance < locus.minimum_alternate_edge_distance_calls
            ):
                locus.minimum_alternate_edge_distance_calls = edge_distance

    for key, locus in mixed.items():
        if locus.alternate_observations != locus.alternate_reads:
            raise ValueError(
                f"{observations_path}: mixed locus {key} expected "
                f"{locus.alternate_reads} alternate observations but saw "
                f"{locus.alternate_observations}"
            )


def locus_audit_rows(
    mixed: dict[tuple[str, int], MixedLocus],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for locus in mixed.values():
        cross_orientation = (
            locus.alternate_forward_observations > 0
            and locus.alternate_reverse_observations > 0
        )
        edge_discordance = (
            locus.alternate_near_read_edge_observations > 0 and not cross_orientation
        )
        rows.append(
            {
                "validation_case_id": locus.validation_case_id,
                "position_1based": locus.position_1based,
                "reference_base": locus.reference_base,
                "reads": locus.reads,
                "reference_reads": locus.reference_reads,
                "alternate_reads": locus.alternate_reads,
                "contributors": locus.contributors,
                "forward_contributors": locus.forward_contributors,
                "reverse_contributors": locus.reverse_contributors,
                "within_profile_impurity": locus.within_profile_impurity,
                "between_profile_dispersion": locus.between_profile_dispersion,
                "total_profile_heterogeneity": locus.total_profile_heterogeneity,
                "directional_profile_distance": locus.directional_profile_distance,
                "alternate_observations": locus.alternate_observations,
                "alternate_forward_observations": (
                    locus.alternate_forward_observations
                ),
                "alternate_reverse_observations": (
                    locus.alternate_reverse_observations
                ),
                "alternate_noisy_observations": locus.alternate_noisy_observations,
                "alternate_near_read_edge_observations": (
                    locus.alternate_near_read_edge_observations
                ),
                "minimum_alternate_edge_distance_calls": (
                    locus.minimum_alternate_edge_distance_calls
                ),
                "cross_orientation_alternate": cross_orientation,
                "edge_discordance": edge_discordance,
                "audit_flags": "edge_discordance" if edge_discordance else "",
            }
        )
    return rows


def p95(values: list[float]) -> float | None:
    return nearest_rank(values, 0.95) if values else None


def case_audit_rows(
    case_geometry: dict[str, CaseGeometry],
    read_rows: list[dict[str, Any]],
    locus_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reads_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_rows:
        reads_by_case[str(row["validation_case_id"])].append(row)
    edge_by_case: dict[str, int] = defaultdict(int)
    for row in locus_rows:
        if row["edge_discordance"]:
            edge_by_case[str(row["validation_case_id"])] += 1

    rows: list[dict[str, Any]] = []
    for case_id, geometry in case_geometry.items():
        reads = reads_by_case.get(case_id, [])
        if not reads:
            raise ValueError(f"case {case_id}: no read audit rows")

        counts = {
            "alignment_challenge_reads": sum(
                bool(row["alignment_challenge"]) for row in reads
            ),
            "high_noise_reads": sum(bool(row["high_noise"]) for row in reads),
            "aggressive_trim_reads": sum(
                bool(row["aggressive_trim"]) for row in reads
            ),
            "short_coverage_reads": sum(
                bool(row["short_coverage"]) for row in reads
            ),
            "orientation_disagreement_reads": sum(
                bool(row["orientation_disagreement"]) for row in reads
            ),
            "unbenchmarked_reads": sum(
                bool(row["unbenchmarked_stratum"]) for row in reads
            ),
        }
        flags = {
            "alignment_challenge": counts["alignment_challenge_reads"] > 0,
            "high_noise": counts["high_noise_reads"] > 0,
            "aggressive_trim": counts["aggressive_trim_reads"] > 0,
            "short_coverage": counts["short_coverage_reads"] > 0,
            "edge_discordance": edge_by_case[case_id] > 0,
            "orientation_disagreement": counts["orientation_disagreement_reads"] > 0,
            "unbenchmarked_stratum": counts["unbenchmarked_reads"] > 0,
        }
        rows.append(
            {
                "validation_case_id": case_id,
                "source_group_id": geometry.source_group_id,
                "specimen_group_id": geometry.specimen_group_id,
                "reads": len(reads),
                "loci": geometry.loci,
                "alternate_loci": geometry.alternate_loci,
                "mixed_loci": geometry.mixed_loci,
                "edge_discordance_loci": edge_by_case[case_id],
                "noisy_loci": geometry.noisy_loci,
                "bidirectional_loci": geometry.bidirectional_loci,
                "p95_within_profile_impurity": p95(geometry.within),
                "p95_between_profile_dispersion": p95(geometry.between),
                "p95_total_profile_heterogeneity": p95(geometry.total),
                "p95_directional_profile_distance": p95(geometry.directional),
                "minimum_callable_identity": min(
                    float(row["callable_identity"]) for row in reads
                ),
                "maximum_noise_rate": max(float(row["noise_rate"]) for row in reads),
                "minimum_retained_fraction": min(
                    float(row["retained_fraction"]) for row in reads
                ),
                "minimum_callable_columns": min(
                    int(row["callable_columns"]) for row in reads
                ),
                **counts,
                **flags,
                "audit_flags": flags_text(flags, CASE_FLAG_ORDER),
            }
        )
    return rows


def flag_counts(
    rows: list[dict[str, Any]],
    flag_names: tuple[str, ...],
) -> dict[str, int]:
    return {
        flag: sum(bool(row.get(flag, False)) for row in rows) for flag in flag_names
    }


__all__ = [
    "AUDIT_SCHEMA_VERSION",
    "CASE_AUDIT_COLUMNS",
    "CASE_FLAG_ORDER",
    "EDGE_DISTANCE_CALLS",
    "LOCUS_AUDIT_COLUMNS",
    "LOWER_AUDIT_QUANTILE",
    "MINIMUM_STRATUM_READS",
    "READ_AUDIT_COLUMNS",
    "READ_FLAG_ORDER",
    "UPPER_AUDIT_QUANTILE",
    "AuditBoundary",
    "RawReadAudit",
    "audit_mixed_observations",
    "case_audit_rows",
    "flag_counts",
    "load_locus_context",
    "locus_audit_rows",
    "read_audit_rows",
    "read_boundaries",
]
