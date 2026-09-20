"""Check direct parity between Rust runtime phase evidence and Python research evidence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validation_corpus.phase_runtime_parity import compare_phase_runtime


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser(description=__doc__)
    built.add_argument(
        "--research-dir",
        type=Path,
        required=True,
        help="completed signal.validation_phase_hypotheses/v1 directory",
    )
    built.add_argument(
        "--runtime-root",
        type=Path,
        required=True,
        help="directory containing *.phase-runtime runtime artifacts",
    )
    built.add_argument(
        "--tolerance",
        type=float,
        default=1e-12,
        help="maximum allowed absolute floating-point delta (default: 1e-12)",
    )
    return built


def runtime_dirs(root: Path) -> list[Path]:
    resolved = root.resolve()
    if not resolved.is_dir():
        raise ValueError(f"runtime root is not a directory: {resolved}")
    found = sorted(
        path for path in resolved.glob("*.phase-runtime") if path.is_dir()
    )
    if not found:
        raise ValueError(f"runtime root contains no *.phase-runtime directories: {resolved}")
    return found


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        summary = compare_phase_runtime(
            args.research_dir.resolve(),
            runtime_dirs(args.runtime_root),
            tolerance=args.tolerance,
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(f"research windows       = {summary.research_windows}")
    print(f"runtime windows        = {summary.runtime_windows}")
    print(f"missing windows        = {summary.missing_windows}")
    print(f"extra windows          = {summary.extra_windows}")
    print(f"call index diff        = {summary.call_index_diffs}")
    print(f"profile count diff     = {summary.profile_observation_diffs}")
    print(f"research candidates    = {summary.research_candidates}")
    print(f"runtime candidates     = {summary.runtime_candidates}")
    print(f"missing candidates     = {summary.missing_candidates}")
    print(f"extra candidates       = {summary.extra_candidates}")
    print(f"candidate count diff   = {summary.candidate_count_diff}")
    print(f"informative count diff = {summary.informative_count_diff}")
    print(f"numeric presence diff  = {summary.numeric_presence_diff}")
    print(f"max numeric delta      = {summary.max_numeric_delta:.17g}")
    print(f"numeric tolerance      = {summary.tolerance:.17g}")
    print(f"parity                 = {'PASS' if summary.passed else 'FAIL'}")
    return 0 if summary.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
