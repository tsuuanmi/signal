"""Evaluate post-poly-C phase hypotheses across an explicit parameter grid."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validation_corpus.phase_sensitivity import (
    DEFAULT_MAX_OFFSETS,
    DEFAULT_WINDOW_SIZES,
    DEFAULT_WINDOW_STEPS,
    publish_phase_sensitivity,
)

ROOT = Path(__file__).resolve().parents[1]


def resolved(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser(description=__doc__)
    built.add_argument(
        "--phase-dir",
        type=Path,
        default=Path("validation-results/research/polyc-phase/baseline"),
        help="completed signal.validation_polyc_phase/v1 directory",
    )
    built.add_argument(
        "--output-dir",
        type=Path,
        default=Path("validation-results/research/polyc-phase-sensitivity/baseline"),
        help="new no-overwrite phase-sensitivity research directory",
    )
    built.add_argument(
        "--window-sizes",
        nargs="+",
        type=int,
        default=list(DEFAULT_WINDOW_SIZES),
        help="profile-bearing observations per window for the full-factorial grid",
    )
    built.add_argument(
        "--window-steps",
        nargs="+",
        type=int,
        default=list(DEFAULT_WINDOW_STEPS),
        help="profile-bearing observations between window starts",
    )
    built.add_argument(
        "--max-offsets",
        nargs="+",
        type=int,
        default=list(DEFAULT_MAX_OFFSETS),
        help="maximum absolute candidate offsets for the full-factorial grid",
    )
    return built


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        publish_phase_sensitivity(
            resolved(args.phase_dir),
            resolved(args.output_dir),
            window_sizes=tuple(args.window_sizes),
            window_steps=tuple(args.window_steps),
            max_offsets=tuple(args.max_offsets),
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"OK phase-sensitivity research: {resolved(args.output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
