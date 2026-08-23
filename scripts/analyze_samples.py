#!/usr/bin/env python3
"""Analyze the first sample IDs from a manifest into per-sample result folders."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def resolved(path: Path) -> Path:
    """Resolve a path relative to the repository root."""
    return path if path.is_absolute() else (ROOT / path).resolve()


def regular_file(path: Path, label: str) -> Path:
    """Require an existing regular file."""
    path = resolved(path)
    if not path.is_file():
        raise ValueError(f"{label} is not a regular file: {path}")
    return path


def displayed(path: Path) -> Path:
    """Prefer a repository-relative path for status output."""
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def sample_ids(manifest: Path, limit: int) -> list[str]:
    """Read and validate the first non-empty sample IDs."""
    if limit < 1:
        raise ValueError("--limit must be at least 1")
    samples = [
        line.strip() for line in manifest.read_text(encoding="utf-8").splitlines()
    ]
    samples = [sample for sample in samples if sample]
    selected = samples[:limit]
    if len(selected) < limit:
        raise ValueError(
            f"manifest contains {len(selected)} non-empty sample IDs; {limit} requested"
        )
    invalid = [sample for sample in selected if SAMPLE_ID.fullmatch(sample) is None]
    if invalid:
        raise ValueError(f"invalid sample ID: {invalid[0]!r}")
    if len(set(selected)) != len(selected):
        raise ValueError("the selected sample IDs are not unique")
    return selected


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser(description=__doc__)
    built.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/MS_010426_001.txt"),
        help="sample ID manifest (default: data/MS_010426_001.txt)",
    )
    built.add_argument(
        "--trace-dir",
        type=Path,
        default=Path("data/raw/MS_010426_001"),
        help="directory containing AB1 files",
    )
    built.add_argument(
        "--reference",
        type=Path,
        default=Path("references/rCRS.fasta"),
        help="reference FASTA",
    )
    built.add_argument(
        "--config",
        type=Path,
        default=Path("config/signal.toml"),
        help="Signal TOML configuration",
    )
    built.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results"),
        help="result root directory",
    )
    built.add_argument(
        "--binary",
        type=Path,
        default=Path("target/release/signal"),
        help="Signal executable",
    )
    built.add_argument("--limit", type=int, default=10, help="number of sample IDs")
    built.add_argument(
        "--no-build",
        action="store_true",
        help="use the existing binary without running cargo build --release",
    )
    return built


def run_analysis(
    binary: Path,
    trace: Path,
    reference: Path,
    config: Path,
    destination: Path,
) -> tuple[bool, str]:
    """Run one analysis in isolation and publish its JSON without overwrite."""
    with tempfile.TemporaryDirectory(prefix="signal-batch-") as temporary:
        work = Path(temporary)
        environment = os.environ.copy()
        environment["SIGNAL_CONFIG"] = str(config)
        completed = subprocess.run(
            [str(binary), "analyze", str(trace), "--reference", str(reference)],
            cwd=work,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or f"exit status {completed.returncode}"
            return False, detail
        generated = work / "results" / f"{trace.stem}.json"
        if not generated.is_file():
            return False, f"analysis succeeded but did not create {generated}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        staged: Path | None = None
        try:
            with (
                generated.open("rb") as source,
                tempfile.NamedTemporaryFile(
                    mode="wb",
                    prefix=f".{destination.stem}.",
                    suffix=".tmp",
                    dir=destination.parent,
                    delete=False,
                ) as target,
            ):
                staged = Path(target.name)
                shutil.copyfileobj(source, target)
                target.flush()
                os.fsync(target.fileno())
            os.link(staged, destination)
        except FileExistsError:
            return False, f"result appeared while analysis was running: {destination}"
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)
    return True, ""


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        manifest = regular_file(args.manifest, "manifest")
        reference = regular_file(args.reference, "reference")
        config = regular_file(args.config, "config")
        trace_dir = resolved(args.trace_dir)
        output_dir = resolved(args.output_dir)
        binary = resolved(args.binary)
        if not trace_dir.is_dir():
            raise ValueError(f"trace directory does not exist: {trace_dir}")
        selected = sample_ids(manifest, args.limit)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if not args.no_build:
        build = subprocess.run(["cargo", "build", "--release"], cwd=ROOT, check=False)
        if build.returncode != 0:
            return build.returncode
    if not binary.is_file():
        print(f"error: Signal binary is not a regular file: {binary}", file=sys.stderr)
        return 2

    completed_count = 0
    skipped_count = 0
    failed_count = 0
    trace_count = 0
    for sample in selected:
        traces = sorted(
            trace for trace in trace_dir.glob(f"*_{sample}_*.ab1") if trace.is_file()
        )
        if not traces:
            print(f"FAIL {sample}: no matching AB1 files", file=sys.stderr)
            failed_count += 1
            continue
        for trace in traces:
            trace_count += 1
            destination = output_dir / sample / f"{trace.stem}.json"
            if destination.exists():
                print(f"SKIP {displayed(destination)}: already exists")
                skipped_count += 1
                continue
            succeeded, detail = run_analysis(
                binary, trace.resolve(), reference, config, destination
            )
            if succeeded:
                print(f"OK   {displayed(destination)}")
                completed_count += 1
            else:
                print(f"FAIL {trace.name}: {detail}", file=sys.stderr)
                failed_count += 1

    print(
        "Summary: "
        f"samples={len(selected)} traces={trace_count} completed={completed_count} "
        f"skipped={skipped_count} failed={failed_count}"
    )
    return 1 if failed_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
