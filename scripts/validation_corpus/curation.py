"""Build a deterministic human-review queue from validation audit evidence."""

from __future__ import annotations

import csv
import json
import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from .audit_analysis import (
    AUDIT_SCHEMA_VERSION,
    CASE_AUDIT_COLUMNS,
    LOCUS_AUDIT_COLUMNS,
    READ_AUDIT_COLUMNS,
)
from .filesystem import file_sha256, sync_directory, validate_new_directory, write_json
from .model import CURATION_QUEUE_SCHEMA_VERSION
from .research_loader import strict_keys

AUDIT_INDEX_FIELDS = (
    "schema_version",
    "source_corpus_sha256",
    "source_research_sha256",
    "signal_version",
    "manifest_sha256",
    "reference_sha256",
    "configuration_sha256",
    "method",
    "read_strata",
    "read_audit_file",
    "read_audit_sha256",
    "read_audit_rows",
    "read_audit_columns",
    "read_flag_counts",
    "locus_audit_file",
    "locus_audit_sha256",
    "locus_audit_rows",
    "locus_audit_columns",
    "locus_flag_counts",
    "case_audit_file",
    "case_audit_sha256",
    "case_audit_rows",
    "case_audit_columns",
    "case_flag_counts",
    "research_loci_rows",
    "research_observations_rows",
)

QUEUE_COLUMNS = (
    "review_item_id",
    "item_type",
    "validation_case_id",
    "position_1based",
    "read_sha256",
    "amplicon_id",
    "declared_direction",
    "review_reasons",
    "audit_flags",
    "recurrence_cases",
    "case_mixed_loci",
    "case_edge_discordance_loci",
    "alternate_observations",
    "alternate_noisy_observations",
    "alternate_near_read_edge_observations",
    "cross_orientation_alternate",
    "minimum_alternate_edge_distance_calls",
    "callable_identity",
    "noise_rate",
    "retained_fraction",
    "callable_columns",
)

DECISION_COLUMNS = (
    "review_item_id",
    "item_type",
    "validation_case_id",
    "review_status",
    "reviewer",
    "truth_source",
    "curation_decision",
    "curation_notes",
)


def json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}: invalid JSON: {error.msg}") from error
    if not isinstance(value, dict):
        raise TypeError(f"{path}: expected a JSON object")
    return value


def load_csv(
    path: Path,
    columns: tuple[str, ...],
    expected_rows: int,
) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"audit CSV is not a regular file: {path}")
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or tuple(reader.fieldnames) != columns:
            raise ValueError(f"{path}: unexpected columns")
        rows = list(reader)
    if len(rows) != expected_rows:
        raise ValueError(
            f"{path}: expected {expected_rows} rows, found {len(rows)}"
        )
    return rows


def nonnegative_int(value: str, label: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{label} must be an integer, got {value!r}") from error
    if parsed < 0:
        raise ValueError(f"{label} must be non-negative")
    return parsed


def boolean(value: str, label: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"{label} must be true or false, got {value!r}")


def validate_audit_source(
    audit_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    index_path = audit_dir / "index.json"
    if not index_path.is_file():
        raise ValueError(f"audit index is not a regular file: {index_path}")
    index = json_object(index_path)
    strict_keys(index, AUDIT_INDEX_FIELDS, "audit index")
    if index["schema_version"] != AUDIT_SCHEMA_VERSION:
        raise ValueError(f"unsupported audit schema: {index['schema_version']!r}")
    if index["read_audit_file"] != "read-audit.csv":
        raise ValueError("audit read file must be read-audit.csv")
    if index["locus_audit_file"] != "locus-audit.csv":
        raise ValueError("audit locus file must be locus-audit.csv")
    if index["case_audit_file"] != "case-audit.csv":
        raise ValueError("audit case file must be case-audit.csv")
    if index["read_audit_columns"] != list(READ_AUDIT_COLUMNS):
        raise ValueError("audit read columns differ from the current contract")
    if index["locus_audit_columns"] != list(LOCUS_AUDIT_COLUMNS):
        raise ValueError("audit locus columns differ from the current contract")
    if index["case_audit_columns"] != list(CASE_AUDIT_COLUMNS):
        raise ValueError("audit case columns differ from the current contract")

    read_path = audit_dir / "read-audit.csv"
    locus_path = audit_dir / "locus-audit.csv"
    case_path = audit_dir / "case-audit.csv"
    for path, field in (
        (read_path, "read_audit_sha256"),
        (locus_path, "locus_audit_sha256"),
        (case_path, "case_audit_sha256"),
    ):
        if index[field] != file_sha256(path):
            raise ValueError(f"{path.name} SHA-256 mismatch")

    reads = load_csv(read_path, READ_AUDIT_COLUMNS, int(index["read_audit_rows"]))
    loci = load_csv(
        locus_path,
        LOCUS_AUDIT_COLUMNS,
        int(index["locus_audit_rows"]),
    )
    cases = load_csv(case_path, CASE_AUDIT_COLUMNS, int(index["case_audit_rows"]))
    return index, reads, loci, cases


def case_context(cases: list[dict[str, str]]) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    for line, row in enumerate(cases, 2):
        case_id = row["validation_case_id"]
        if not case_id or case_id in result:
            raise ValueError(f"case-audit.csv:{line}: invalid or duplicate case ID")
        result[case_id] = (
            nonnegative_int(row["mixed_loci"], f"case-audit.csv:{line}.mixed_loci"),
            nonnegative_int(
                row["edge_discordance_loci"],
                f"case-audit.csv:{line}.edge_discordance_loci",
            ),
        )
    return result


def locus_recurrence(loci: list[dict[str, str]]) -> dict[int, int]:
    cases_by_position: dict[int, set[str]] = {}
    seen: set[tuple[str, int]] = set()
    for line, row in enumerate(loci, 2):
        case_id = row["validation_case_id"]
        position = nonnegative_int(
            row["position_1based"],
            f"locus-audit.csv:{line}.position_1based",
        )
        key = (case_id, position)
        if not case_id or key in seen:
            raise ValueError(f"locus-audit.csv:{line}: invalid or duplicate locus")
        seen.add(key)
        cases_by_position.setdefault(position, set()).add(case_id)
    return {position: len(case_ids) for position, case_ids in cases_by_position.items()}


def locus_reasons(row: dict[str, str], recurrence: int, label: str) -> str:
    reasons = ["mixed_locus"]
    if recurrence > 1:
        reasons.append("recurrent_mixed_locus")
    if boolean(row["edge_discordance"], f"{label}.edge_discordance"):
        reasons.append("edge_discordance")
    if nonnegative_int(
        row["alternate_noisy_observations"],
        f"{label}.alternate_noisy_observations",
    ):
        reasons.append("noisy_alternate")
    if not boolean(
        row["cross_orientation_alternate"],
        f"{label}.cross_orientation_alternate",
    ):
        reasons.append("single_orientation_alternate")
    return ";".join(reasons)


def locus_queue_rows(
    loci: list[dict[str, str]],
    cases: dict[str, tuple[int, int]],
) -> list[dict[str, Any]]:
    recurrence = locus_recurrence(loci)
    rows: list[dict[str, Any]] = []
    for line, row in enumerate(loci, 2):
        label = f"locus-audit.csv:{line}"
        case_id = row["validation_case_id"]
        if case_id not in cases:
            raise ValueError(f"{label}: unknown validation case {case_id!r}")
        position = nonnegative_int(row["position_1based"], f"{label}.position_1based")
        mixed_loci, edge_loci = cases[case_id]
        rows.append(
            {
                "review_item_id": f"locus:{case_id}:{position}",
                "item_type": "mixed_locus",
                "validation_case_id": case_id,
                "position_1based": position,
                "read_sha256": "",
                "amplicon_id": "",
                "declared_direction": "",
                "review_reasons": locus_reasons(
                    row,
                    recurrence[position],
                    label,
                ),
                "audit_flags": row["audit_flags"],
                "recurrence_cases": recurrence[position],
                "case_mixed_loci": mixed_loci,
                "case_edge_discordance_loci": edge_loci,
                "alternate_observations": nonnegative_int(
                    row["alternate_observations"],
                    f"{label}.alternate_observations",
                ),
                "alternate_noisy_observations": nonnegative_int(
                    row["alternate_noisy_observations"],
                    f"{label}.alternate_noisy_observations",
                ),
                "alternate_near_read_edge_observations": nonnegative_int(
                    row["alternate_near_read_edge_observations"],
                    f"{label}.alternate_near_read_edge_observations",
                ),
                "cross_orientation_alternate": row["cross_orientation_alternate"],
                "minimum_alternate_edge_distance_calls": (
                    row["minimum_alternate_edge_distance_calls"]
                ),
                "callable_identity": "",
                "noise_rate": "",
                "retained_fraction": "",
                "callable_columns": "",
            }
        )
    rows.sort(
        key=lambda row: (
            -int(row["recurrence_cases"]),
            int(row["position_1based"]),
            str(row["validation_case_id"]),
        )
    )
    return rows


def read_queue_rows(
    reads: list[dict[str, str]],
    cases: dict[str, tuple[int, int]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line, row in enumerate(reads, 2):
        flags = row["audit_flags"]
        if not flags:
            continue
        label = f"read-audit.csv:{line}"
        case_id = row["validation_case_id"]
        read_sha256 = row["read_sha256"]
        if case_id not in cases:
            raise ValueError(f"{label}: unknown validation case {case_id!r}")
        if not read_sha256 or read_sha256 in seen:
            raise ValueError(f"{label}: invalid or duplicate read SHA-256")
        seen.add(read_sha256)
        mixed_loci, edge_loci = cases[case_id]
        rows.append(
            {
                "review_item_id": f"read:{read_sha256}",
                "item_type": "read",
                "validation_case_id": case_id,
                "position_1based": "",
                "read_sha256": read_sha256,
                "amplicon_id": row["amplicon_id"],
                "declared_direction": row["declared_direction"],
                "review_reasons": flags,
                "audit_flags": flags,
                "recurrence_cases": "",
                "case_mixed_loci": mixed_loci,
                "case_edge_discordance_loci": edge_loci,
                "alternate_observations": "",
                "alternate_noisy_observations": "",
                "alternate_near_read_edge_observations": "",
                "cross_orientation_alternate": "",
                "minimum_alternate_edge_distance_calls": "",
                "callable_identity": row["callable_identity"],
                "noise_rate": row["noise_rate"],
                "retained_fraction": row["retained_fraction"],
                "callable_columns": row["callable_columns"],
            }
        )
    rows.sort(
        key=lambda row: (
            str(row["validation_case_id"]),
            str(row["amplicon_id"]),
            str(row["declared_direction"]),
            str(row["read_sha256"]),
        )
    )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], columns: tuple[str, ...]) -> None:
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
                raise ValueError(f"curation row {index} does not match output columns")
            writer.writerow(row)
        target.flush()
        os.fsync(target.fileno())


def decisions_template(queue_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "review_item_id": row["review_item_id"],
            "item_type": row["item_type"],
            "validation_case_id": row["validation_case_id"],
            "review_status": "",
            "reviewer": "",
            "truth_source": "",
            "curation_decision": "",
            "curation_notes": "",
        }
        for row in queue_rows
    ]


def queue_index(
    audit_dir: Path,
    audit_index: dict[str, Any],
    queue_path: Path,
    decisions_path: Path,
    queue_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    counts = Counter(str(row["item_type"]) for row in queue_rows)
    return {
        "schema_version": CURATION_QUEUE_SCHEMA_VERSION,
        "source_audit_sha256": file_sha256(audit_dir / "index.json"),
        "source_corpus_sha256": audit_index["source_corpus_sha256"],
        "source_research_sha256": audit_index["source_research_sha256"],
        "signal_version": audit_index["signal_version"],
        "manifest_sha256": audit_index["manifest_sha256"],
        "reference_sha256": audit_index["reference_sha256"],
        "configuration_sha256": audit_index["configuration_sha256"],
        "method": {
            "included_items": [
                "every mixed locus in locus-audit.csv",
                "every read with non-empty audit_flags in read-audit.csv",
            ],
            "locus_order": [
                "recurrence_cases descending",
                "position_1based ascending",
                "validation_case_id ascending",
            ],
            "read_order": [
                "validation_case_id ascending",
                "amplicon_id ascending",
                "declared_direction ascending",
                "read_sha256 ascending",
            ],
            "automatic_truth_assignment": False,
            "automatic_exclusion": False,
        },
        "queue_file": "curation-queue.csv",
        "queue_sha256": file_sha256(queue_path),
        "queue_rows": len(queue_rows),
        "queue_columns": list(QUEUE_COLUMNS),
        "item_counts": dict(sorted(counts.items())),
        "decisions_template_file": "curation-decisions-template.csv",
        "decisions_template_sha256": file_sha256(decisions_path),
        "decisions_template_rows": len(queue_rows),
        "decisions_template_columns": list(DECISION_COLUMNS),
    }


def publish_curation_queue(audit_dir: Path, output_dir: Path) -> None:
    audit_dir = audit_dir.resolve()
    output_dir = output_dir.resolve()
    if not audit_dir.is_dir():
        raise ValueError(f"audit directory does not exist: {audit_dir}")
    validate_new_directory(output_dir, (audit_dir,))
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if not output_dir.parent.is_dir() or output_dir.parent.is_symlink():
        raise ValueError(
            f"output parent is not a regular directory: {output_dir.parent}"
        )

    audit_index, reads, loci, cases = validate_audit_source(audit_dir)
    case_map = case_context(cases)
    queue_rows = locus_queue_rows(loci, case_map) + read_queue_rows(reads, case_map)
    if not queue_rows:
        raise ValueError("audit contains no mixed loci or flagged reads to review")

    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        queue_path = stage / "curation-queue.csv"
        decisions_path = stage / "curation-decisions-template.csv"
        write_csv(queue_path, queue_rows, QUEUE_COLUMNS)
        write_csv(decisions_path, decisions_template(queue_rows), DECISION_COLUMNS)
        write_json(
            stage / "index.json",
            queue_index(
                audit_dir,
                audit_index,
                queue_path,
                decisions_path,
                queue_rows,
            ),
        )
        sync_directory(stage)

        try:
            output_dir.mkdir()
        except FileExistsError as error:
            raise FileExistsError(
                f"output directory appeared while curation queue was running: "
                f"{output_dir}"
            ) from error
        try:
            for name in (
                "curation-queue.csv",
                "curation-decisions-template.csv",
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
