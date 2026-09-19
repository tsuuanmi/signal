#!/usr/bin/env python3
"""Run a provenanced local Signal validation corpus."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from validation_corpus.filesystem import validate_new_directory
from validation_corpus.manifest import load_manifest, select_cases
from validation_corpus.runner import run_corpus

ROOT = Path(__file__).resolve().parents[1]


def resolved(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def regular_file(path: Path, label: str) -> Path:
    resolved_path = resolved(path)
    if not resolved_path.is_file():
        raise ValueError(f"{label} is not a regular file: {resolved_path}")
    return resolved_path


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser(description=__doc__)
    built.add_argument(
        "--manifest", type=Path, required=True, help="validation CSV manifest"
    )
    built.add_argument(
        "--reference",
        type=Path,
        default=Path("references/rCRS.fasta"),
        help="reference FASTA (default: references/rCRS.fasta)",
    )
    built.add_argument(
        "--config",
        type=Path,
        default=Path("config/signal.toml"),
        help="Signal TOML configuration (default: config/signal.toml)",
    )
    built.add_argument(
        "--binary",
        type=Path,
        default=Path("target/release/signal-validation"),
        help="validation executable (default: target/release/signal-validation)",
    )
    built.add_argument(
        "--output-dir",
        type=Path,
        default=Path("validation-results/corpus"),
        help="atomic corpus output directory",
    )
    built.add_argument(
        "--case",
        action="append",
        dest="cases",
        help="run only the named validation case; repeat to select multiple cases",
    )
    built.add_argument("--limit", type=int, help="run only the first N selected cases")
    built.add_argument(
        "--no-build",
        action="store_true",
        help="use the existing validation binary without running cargo build --release",
    )
    return built


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        manifest = regular_file(args.manifest, "manifest")
        reference = regular_file(args.reference, "reference")
        config = regular_file(args.config, "config")
        cases = select_cases(load_manifest(manifest), args.cases, args.limit)
        output_dir = resolved(args.output_dir)
        binary = resolved(args.binary)
        validate_new_directory(
            output_dir,
            (
                manifest,
                reference,
                config,
                *(trace.path for case in cases for trace in case.traces),
            ),
        )
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if not args.no_build:
        build = subprocess.run(
            ["cargo", "build", "--release", "--bin", "signal-validation"],
            cwd=ROOT,
            check=False,
        )
        if build.returncode != 0:
            return build.returncode
    if not binary.is_file():
        print(
            f"error: validation binary is not a regular file: {binary}",
            file=sys.stderr,
        )
        return 2

    try:
        run_corpus(manifest, cases, reference, config, binary, output_dir)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(
        f"OK validation corpus: cases={len(cases)} "
        f"traces={sum(len(case.traces) for case in cases)} output={output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
