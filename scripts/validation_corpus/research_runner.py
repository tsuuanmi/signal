"""Build and publish deterministic joined validation research datasets."""

from __future__ import annotations

import csv
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, TextIO

from .filesystem import (
    file_sha256,
    sync_directory,
    validate_new_directory,
    write_json,
)
from .research_loader import iter_research_rows, load_research_corpus
from .research_model import (
    LOCUS_TABLE_COLUMNS,
    OBSERVATION_TABLE_COLUMNS,
    RESEARCH_SCHEMA_VERSION,
    ResearchCorpus,
)
from .research_statistics import ResearchStatisticsAccumulator


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
            f"{label} does not match table columns: missing={missing} extra={extra}"
        )
    target.writerow({key: csv_value(row[key]) for key in columns})


def research_index(
    corpus: ResearchCorpus,
    loci_path: Path,
    observations_path: Path,
    loci_count: int,
    observations_count: int,
    statistics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": RESEARCH_SCHEMA_VERSION,
        "source_corpus_sha256": file_sha256(corpus.index_path),
        "signal_version": corpus.signal_version,
        "manifest_sha256": corpus.manifest_sha256,
        "reference_sha256": corpus.reference_sha256,
        "configuration_sha256": corpus.configuration_sha256,
        "loci_file": "loci.csv",
        "loci_sha256": file_sha256(loci_path),
        "loci_rows": loci_count,
        "loci_columns": list(LOCUS_TABLE_COLUMNS),
        "observations_file": "observations.csv",
        "observations_sha256": file_sha256(observations_path),
        "observations_rows": observations_count,
        "observations_columns": list(OBSERVATION_TABLE_COLUMNS),
        "statistics": statistics,
    }


def build_staged_research(corpus: ResearchCorpus, stage: Path) -> None:
    loci_path = stage / "loci.csv"
    observations_path = stage / "observations.csv"
    statistics = ResearchStatisticsAccumulator()
    loci_count = 0
    observations_count = 0

    with (
        loci_path.open("x", encoding="utf-8", newline="") as loci_file,
        observations_path.open("x", encoding="utf-8", newline="") as observations_file,
    ):
        loci_writer = writer(loci_file, LOCUS_TABLE_COLUMNS)
        observations_writer = writer(observations_file, OBSERVATION_TABLE_COLUMNS)

        for locus_row, observation_rows in iter_research_rows(corpus):
            write_row(
                loci_writer,
                locus_row,
                LOCUS_TABLE_COLUMNS,
                f"locus row {loci_count}",
            )
            statistics.add(locus_row)
            loci_count += 1
            for observation_row in observation_rows:
                write_row(
                    observations_writer,
                    observation_row,
                    OBSERVATION_TABLE_COLUMNS,
                    f"observation row {observations_count}",
                )
                observations_count += 1

        loci_file.flush()
        os.fsync(loci_file.fileno())
        observations_file.flush()
        os.fsync(observations_file.fileno())

    write_json(
        stage / "index.json",
        research_index(
            corpus,
            loci_path,
            observations_path,
            loci_count,
            observations_count,
            statistics.result(),
        ),
    )
    sync_directory(stage)


def publish_research(corpus_dir: Path, output_dir: Path) -> None:
    corpus_dir = corpus_dir.resolve()
    output_dir = output_dir.resolve()
    if not corpus_dir.is_dir():
        raise ValueError(f"corpus directory does not exist: {corpus_dir}")
    validate_new_directory(output_dir, (corpus_dir,))
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if not output_dir.parent.is_dir() or output_dir.parent.is_symlink():
        raise ValueError(f"output parent is not a regular directory: {output_dir.parent}")

    corpus = load_research_corpus(corpus_dir)
    stage = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent)
    )
    try:
        build_staged_research(corpus, stage)
        try:
            output_dir.mkdir()
        except FileExistsError as error:
            raise FileExistsError(
                f"output directory appeared while research analysis was running: "
                f"{output_dir}"
            ) from error
        try:
            for name in ("loci.csv", "observations.csv", "index.json"):
                os.rename(stage / name, output_dir / name)
            sync_directory(output_dir)
            sync_directory(output_dir.parent)
        except OSError:
            shutil.rmtree(output_dir, ignore_errors=True)
            sync_directory(output_dir.parent)
            raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
