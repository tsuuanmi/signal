"""Build and publish deterministic validation audit strata."""

from __future__ import annotations

import csv
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .audit_analysis import (
    AUDIT_SCHEMA_VERSION,
    CASE_AUDIT_COLUMNS,
    CASE_FLAG_ORDER,
    EDGE_DISTANCE_CALLS,
    LOCUS_AUDIT_COLUMNS,
    LOWER_AUDIT_QUANTILE,
    MINIMUM_STRATUM_READS,
    READ_AUDIT_COLUMNS,
    READ_FLAG_ORDER,
    UPPER_AUDIT_QUANTILE,
    AuditBoundary,
    audit_mixed_observations,
    case_audit_rows,
    flag_counts,
    load_locus_context,
    locus_audit_rows,
    read_audit_rows,
    read_boundaries,
)
from .audit_logs import load_read_audits
from .filesystem import file_sha256, sync_directory, validate_new_directory, write_json
from .model import RESEARCH_SCHEMA_VERSION
from .research_loader import load_research_corpus, strict_keys
from .research_model import (
    LOCUS_TABLE_COLUMNS,
    OBSERVATION_TABLE_COLUMNS,
    ResearchCorpus,
)

RESEARCH_INDEX_FIELDS = (
    "schema_version",
    "source_corpus_sha256",
    "signal_version",
    "manifest_sha256",
    "reference_sha256",
    "configuration_sha256",
    "loci_file",
    "loci_sha256",
    "loci_rows",
    "loci_columns",
    "observations_file",
    "observations_sha256",
    "observations_rows",
    "observations_columns",
    "statistics",
)


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}: invalid JSON: {error.msg}") from error
    if not isinstance(value, dict):
        raise TypeError(f"{path}: expected a JSON object")
    return value


def validate_research_source(
    corpus: ResearchCorpus,
    research_dir: Path,
) -> tuple[dict[str, Any], Path, Path]:
    index_path = research_dir / "index.json"
    if not index_path.is_file():
        raise ValueError(f"research index is not a regular file: {index_path}")
    index = load_json_object(index_path)
    strict_keys(index, RESEARCH_INDEX_FIELDS, "research index")
    if index["schema_version"] != RESEARCH_SCHEMA_VERSION:
        raise ValueError(f"unsupported research schema: {index['schema_version']!r}")
    if index["source_corpus_sha256"] != file_sha256(corpus.index_path):
        raise ValueError("research index does not match the supplied corpus index")
    for field, expected in (
        ("signal_version", corpus.signal_version),
        ("manifest_sha256", corpus.manifest_sha256),
        ("reference_sha256", corpus.reference_sha256),
        ("configuration_sha256", corpus.configuration_sha256),
    ):
        if index[field] != expected:
            raise ValueError(f"research {field} differs from corpus identity")

    if index["loci_file"] != "loci.csv":
        raise ValueError("research loci file must be loci.csv")
    if index["observations_file"] != "observations.csv":
        raise ValueError("research observations file must be observations.csv")
    if index["loci_columns"] != list(LOCUS_TABLE_COLUMNS):
        raise ValueError("research loci_columns do not match the current contract")
    if index["observations_columns"] != list(OBSERVATION_TABLE_COLUMNS):
        raise ValueError(
            "research observations_columns do not match the current contract"
        )

    loci_path = research_dir / "loci.csv"
    observations_path = research_dir / "observations.csv"
    if not loci_path.is_file() or not observations_path.is_file():
        raise ValueError("research CSV files are missing")
    if index["loci_sha256"] != file_sha256(loci_path):
        raise ValueError("research loci.csv SHA-256 mismatch")
    if index["observations_sha256"] != file_sha256(observations_path):
        raise ValueError("research observations.csv SHA-256 mismatch")
    return index, loci_path, observations_path


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    columns: tuple[str, ...],
) -> None:
    expected = set(columns)
    with path.open("x", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(
            target,
            fieldnames=list(columns),
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        for index, row in enumerate(rows):
            if set(row) != expected:
                missing = sorted(expected - set(row))
                extra = sorted(set(row) - expected)
                raise ValueError(
                    f"audit row {index} does not match columns: "
                    f"missing={missing} extra={extra}"
                )
            writer.writerow({key: csv_value(row[key]) for key in columns})
        target.flush()
        os.fsync(target.fileno())


def stratum_index(
    boundaries: dict[tuple[str, str], AuditBoundary],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for (amplicon_id, direction), boundary in sorted(boundaries.items()):
        benchmarked = boundary.n >= MINIMUM_STRATUM_READS
        records.append(
            {
                "amplicon_id": amplicon_id,
                "declared_direction": direction,
                "n": boundary.n,
                "benchmarked": benchmarked,
                "identity_p05": boundary.identity_p05 if benchmarked else None,
                "noise_p95": boundary.noise_p95 if benchmarked else None,
                "retained_fraction_p05": (
                    boundary.retained_fraction_p05 if benchmarked else None
                ),
                "callable_columns_p05": (
                    boundary.callable_columns_p05 if benchmarked else None
                ),
            }
        )
    return records


def audit_index(
    corpus: ResearchCorpus,
    research_dir: Path,
    research_index: dict[str, Any],
    boundaries: dict[tuple[str, str], AuditBoundary],
    read_path: Path,
    locus_path: Path,
    case_path: Path,
    read_rows: list[dict[str, Any]],
    locus_rows: list[dict[str, Any]],
    case_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "source_corpus_sha256": file_sha256(corpus.index_path),
        "source_research_sha256": file_sha256(research_dir / "index.json"),
        "signal_version": corpus.signal_version,
        "manifest_sha256": corpus.manifest_sha256,
        "reference_sha256": corpus.reference_sha256,
        "configuration_sha256": corpus.configuration_sha256,
        "method": {
            "read_strata": ["amplicon_id", "declared_direction"],
            "minimum_stratum_reads": MINIMUM_STRATUM_READS,
            "quantile_method": "empirical_nearest_rank",
            "lower_audit_quantile": LOWER_AUDIT_QUANTILE,
            "upper_audit_quantile": UPPER_AUDIT_QUANTILE,
            "edge_distance_calls": EDGE_DISTANCE_CALLS,
            "rules": {
                "alignment_challenge": ("callable_identity <= stratum empirical p05"),
                "high_noise": "noise_rate >= stratum empirical p95",
                "aggressive_trim": ("retained_fraction <= stratum empirical p05"),
                "short_coverage": "callable_columns <= stratum empirical p05",
                "edge_discordance": (
                    "mixed reference/alternate locus with alternate evidence "
                    "within retained-read edge distance and no alternate support "
                    "from both orientations"
                ),
                "orientation_disagreement": (
                    "inferred orientation differs from declared validation metadata"
                ),
                "unbenchmarked_stratum": (
                    "read stratum has fewer than minimum_stratum_reads"
                ),
            },
        },
        "read_strata": stratum_index(boundaries),
        "read_audit_file": "read-audit.csv",
        "read_audit_sha256": file_sha256(read_path),
        "read_audit_rows": len(read_rows),
        "read_audit_columns": list(READ_AUDIT_COLUMNS),
        "read_flag_counts": flag_counts(read_rows, READ_FLAG_ORDER),
        "locus_audit_file": "locus-audit.csv",
        "locus_audit_sha256": file_sha256(locus_path),
        "locus_audit_rows": len(locus_rows),
        "locus_audit_columns": list(LOCUS_AUDIT_COLUMNS),
        "locus_flag_counts": {
            "edge_discordance": sum(bool(row["edge_discordance"]) for row in locus_rows)
        },
        "case_audit_file": "case-audit.csv",
        "case_audit_sha256": file_sha256(case_path),
        "case_audit_rows": len(case_rows),
        "case_audit_columns": list(CASE_AUDIT_COLUMNS),
        "case_flag_counts": flag_counts(case_rows, CASE_FLAG_ORDER),
        "research_loci_rows": research_index["loci_rows"],
        "research_observations_rows": research_index["observations_rows"],
    }


def build_staged_audit(
    corpus_dir: Path,
    research_dir: Path,
    stage: Path,
) -> None:
    corpus = load_research_corpus(corpus_dir)
    research_index, loci_path, observations_path = validate_research_source(
        corpus, research_dir
    )
    raw_reads = load_read_audits(corpus, corpus_dir)
    boundaries = read_boundaries(raw_reads)
    read_rows = read_audit_rows(raw_reads, boundaries)
    reads_by_sha256 = {record.read_sha256: record for record in raw_reads}

    case_geometry, mixed = load_locus_context(loci_path)
    audit_mixed_observations(observations_path, mixed, reads_by_sha256)
    locus_rows = locus_audit_rows(mixed)
    case_rows = case_audit_rows(case_geometry, read_rows, locus_rows)

    read_path = stage / "read-audit.csv"
    locus_path = stage / "locus-audit.csv"
    case_path = stage / "case-audit.csv"
    write_csv(read_path, read_rows, READ_AUDIT_COLUMNS)
    write_csv(locus_path, locus_rows, LOCUS_AUDIT_COLUMNS)
    write_csv(case_path, case_rows, CASE_AUDIT_COLUMNS)
    write_json(
        stage / "index.json",
        audit_index(
            corpus,
            research_dir,
            research_index,
            boundaries,
            read_path,
            locus_path,
            case_path,
            read_rows,
            locus_rows,
            case_rows,
        ),
    )
    sync_directory(stage)


def publish_audit(
    corpus_dir: Path,
    research_dir: Path,
    output_dir: Path,
) -> None:
    corpus_dir = corpus_dir.resolve()
    research_dir = research_dir.resolve()
    output_dir = output_dir.resolve()
    if not corpus_dir.is_dir():
        raise ValueError(f"corpus directory does not exist: {corpus_dir}")
    if not research_dir.is_dir():
        raise ValueError(f"research directory does not exist: {research_dir}")
    validate_new_directory(output_dir, (corpus_dir, research_dir))
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if not output_dir.parent.is_dir() or output_dir.parent.is_symlink():
        raise ValueError(
            f"output parent is not a regular directory: {output_dir.parent}"
        )

    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        build_staged_audit(corpus_dir, research_dir, stage)
        try:
            output_dir.mkdir()
        except FileExistsError as error:
            raise FileExistsError(
                f"output directory appeared while audit was running: {output_dir}"
            ) from error
        try:
            for name in (
                "read-audit.csv",
                "locus-audit.csv",
                "case-audit.csv",
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
