"""Validation measurement integrity checks and corpus provenance index assembly."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .filesystem import file_sha256
from .model import (
    CORPUS_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    MEASUREMENT_SCHEMA_VERSION,
    MeasurementSummary,
    ValidationCase,
)

SHA256 = re.compile(r"^[0-9a-f]{64}$")


def measurement_summary(path: Path, case: ValidationCase) -> MeasurementSummary:
    expected_reads = {trace.trace_sha256 for trace in case.traces}
    seen_reads: set[str] = set()
    identity: tuple[str, str, str, str] | None = None
    previous_position = 0
    loci = 0

    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                raise ValueError(f"{path}: empty measurement row at line {line_number}")
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"{path}: invalid JSON at line {line_number}: {error.msg}"
                ) from error
            if not isinstance(row, dict):
                raise TypeError(f"{path}: line {line_number} is not a JSON object")
            if row.get("schema_version") != MEASUREMENT_SCHEMA_VERSION:
                raise ValueError(
                    f"{path}: line {line_number} has unexpected measurement schema "
                    f"{row.get('schema_version')!r}"
                )
            if row.get("sample_id") != case.metadata.validation_case_id:
                raise ValueError(
                    f"{path}: line {line_number} has sample_id {row.get('sample_id')!r}"
                )

            position = row.get("position_1based")
            if (
                not isinstance(position, int)
                or isinstance(position, bool)
                or position <= previous_position
            ):
                raise ValueError(
                    f"{path}: positions must be strictly increasing positive integers"
                )
            previous_position = position

            signal_version = row.get("signal_version")
            reference_sha256 = row.get("reference_sha256")
            configuration_sha256 = row.get("configuration_sha256")
            if not isinstance(signal_version, str) or not signal_version:
                raise ValueError(f"{path}: line {line_number} lacks signal_version")
            if (
                not isinstance(reference_sha256, str)
                or SHA256.fullmatch(reference_sha256) is None
            ):
                raise ValueError(
                    f"{path}: line {line_number} has invalid reference_sha256"
                )
            if (
                not isinstance(configuration_sha256, str)
                or SHA256.fullmatch(configuration_sha256) is None
            ):
                raise ValueError(
                    f"{path}: line {line_number} has invalid configuration_sha256"
                )
            current_identity = (
                MEASUREMENT_SCHEMA_VERSION,
                signal_version,
                reference_sha256,
                configuration_sha256,
            )
            if identity is None:
                identity = current_identity
            elif current_identity != identity:
                raise ValueError(f"{path}: export identity changes within one file")

            observations = row.get("observations")
            if not isinstance(observations, list):
                raise TypeError(f"{path}: line {line_number} lacks observations[]")
            reads = row.get("reads")
            if (
                not isinstance(reads, int)
                or isinstance(reads, bool)
                or reads != len(observations)
            ):
                raise ValueError(
                    f"{path}: line {line_number} read count does not match observations"
                )

            row_reads: set[str] = set()
            for observation in observations:
                if not isinstance(observation, dict):
                    raise TypeError(
                        f"{path}: line {line_number} has a non-object observation"
                    )
                read_sha256 = observation.get("read_sha256")
                if (
                    not isinstance(read_sha256, str)
                    or read_sha256 not in expected_reads
                ):
                    raise ValueError(
                        f"{path}: line {line_number} references unexpected read SHA-256"
                    )
                if read_sha256 in row_reads:
                    raise ValueError(
                        f"{path}: line {line_number} repeats one read observation"
                    )
                row_reads.add(read_sha256)
                seen_reads.add(read_sha256)
            loci += 1

    if loci == 0 or identity is None:
        raise ValueError(f"{path}: measurement export contains no loci")
    missing_reads = expected_reads - seen_reads
    if missing_reads:
        raise ValueError(
            f"{path}: measurement export never references "
            f"{len(missing_reads)} manifest trace(s)"
        )
    return MeasurementSummary(*identity, loci)


def corpus_index(
    manifest: Path,
    cases: list[ValidationCase],
    summaries: list[MeasurementSummary],
) -> dict[str, Any]:
    if not summaries:
        raise ValueError("validation corpus has no measurement summaries")
    first = summaries[0]
    for summary in summaries[1:]:
        if summary.schema_version != first.schema_version:
            raise ValueError(
                "measurement schema version differs across validation cases"
            )
        if summary.signal_version != first.signal_version:
            raise ValueError("Signal version differs across validation cases")
        if summary.reference_sha256 != first.reference_sha256:
            raise ValueError("reference SHA-256 differs across validation cases")
        if summary.configuration_sha256 != first.configuration_sha256:
            raise ValueError("configuration SHA-256 differs across validation cases")

    records: list[dict[str, Any]] = []
    for case, summary in zip(cases, summaries, strict=True):
        record = case.metadata.index_record()
        record["measurement_file"] = f"cases/{case.metadata.validation_case_id}.jsonl"
        record["loci"] = summary.loci
        record["reads"] = [trace.index_record() for trace in case.traces]
        records.append(record)

    return {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "measurement_schema_version": first.schema_version,
        "signal_version": first.signal_version,
        "manifest_sha256": file_sha256(manifest),
        "reference_sha256": first.reference_sha256,
        "configuration_sha256": first.configuration_sha256,
        "case_count": len(cases),
        "trace_count": sum(len(case.traces) for case in cases),
        "cases": records,
    }
