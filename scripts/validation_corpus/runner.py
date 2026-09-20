"""Isolated execution and all-or-nothing publication of local validation corpora."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .filesystem import sync_directory, validate_new_directory, write_bytes, write_json
from .measurements import corpus_index, load_measurements
from .model import MeasurementSummary, ValidationCase


def run_case(
    binary: Path,
    case: ValidationCase,
    reference: Path,
    config: Path,
    work_root: Path,
    publish_root: Path,
) -> MeasurementSummary:
    case_id = case.metadata.validation_case_id
    work = work_root / case_id
    work.mkdir()
    log_dir = publish_root / "logs"
    log_dir.mkdir(exist_ok=True)
    environment = os.environ.copy()
    environment["SIGNAL_CONFIG"] = str(config)
    environment["SIGNAL_LOG_DIR"] = str(log_dir)
    completed = subprocess.run(
        [
            str(binary),
            case_id,
            *(str(trace.path) for trace in case.traces),
            "--reference",
            str(reference),
        ],
        cwd=work,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or f"exit status {completed.returncode}"
        raise RuntimeError(f"{case_id}: signal-validation failed: {detail}")

    generated_root = work / "validation-results"
    generated = generated_root / f"{case_id}.jsonl"
    if not generated.is_file():
        raise RuntimeError(
            f"{case_id}: validation succeeded but did not create {generated}"
        )
    phase_runtime = generated_root / f"{case_id}.phase-runtime"
    if not phase_runtime.is_dir() or phase_runtime.is_symlink():
        raise RuntimeError(
            f"{case_id}: validation succeeded but did not create {phase_runtime}"
        )
    for filename in ("index.json", "windows.csv", "candidates.csv"):
        path = phase_runtime / filename
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(
                f"{case_id}: validation phase runtime is missing {path}"
            )

    expected_reads = {trace.trace_sha256 for trace in case.traces}
    summary = load_measurements(
        generated, case.metadata.validation_case_id, expected_reads
    ).summary
    cases_dir = publish_root / "cases"
    cases_dir.mkdir(exist_ok=True)
    write_bytes(cases_dir / f"{case_id}.jsonl", generated.read_bytes())

    phase_runtime_dir = publish_root / "phase-runtime"
    phase_runtime_dir.mkdir(exist_ok=True)
    os.rename(
        phase_runtime,
        phase_runtime_dir / f"{case_id}.phase-runtime",
    )
    return summary


def run_corpus(
    manifest: Path,
    cases: list[ValidationCase],
    reference: Path,
    config: Path,
    binary: Path,
    output_dir: Path,
) -> None:
    output_dir = output_dir.resolve()
    protected = (
        manifest,
        reference,
        config,
        binary,
        *(trace.path for case in cases for trace in case.traces),
    )
    validate_new_directory(output_dir, protected)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if not output_dir.parent.is_dir() or output_dir.parent.is_symlink():
        raise ValueError(
            f"output parent is not a regular directory: {output_dir.parent}"
        )

    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    publish_root = stage / "publish"
    work_root = stage / "work"
    publish_root.mkdir()
    work_root.mkdir()
    try:
        summaries = [
            run_case(binary, case, reference, config, work_root, publish_root)
            for case in cases
        ]
        write_json(
            publish_root / "index.json", corpus_index(manifest, cases, summaries)
        )
        for runtime in (publish_root / "phase-runtime").glob("*.phase-runtime"):
            sync_directory(runtime)
        for directory in (
            publish_root / "cases",
            publish_root / "logs",
            publish_root / "phase-runtime",
            publish_root,
        ):
            if directory.exists():
                sync_directory(directory)

        try:
            output_dir.mkdir()
        except FileExistsError as error:
            raise FileExistsError(
                f"output directory appeared while running: {output_dir}"
            ) from error
        try:
            for name in ("cases", "logs", "phase-runtime"):
                source = publish_root / name
                if source.exists():
                    os.rename(source, output_dir / name)
            os.rename(publish_root / "index.json", output_dir / "index.json")
            sync_directory(output_dir)
            sync_directory(output_dir.parent)
        except OSError:
            shutil.rmtree(output_dir, ignore_errors=True)
            sync_directory(output_dir.parent)
            raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
