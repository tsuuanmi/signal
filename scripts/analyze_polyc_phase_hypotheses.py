"""Build Tracy-inspired post-poly-C candidate phase-hypothesis curves."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validation_corpus.phase_hypotheses import publish_phase_hypotheses

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
        default=Path("validation-results/research/polyc-phase-hypotheses/baseline"),
        help="new no-overwrite phase-hypothesis research directory",
    )
    built.add_argument(
        "--window-size",
        type=int,
        default=25,
        help="profile-bearing observations per downstream window",
    )
    built.add_argument(
        "--window-step",
        type=int,
        default=5,
        help="profile-bearing observations between window starts",
    )
    built.add_argument(
        "--max-offset",
        type=int,
        default=5,
        help="evaluate reference offsets from -N through +N excluding zero",
    )
    return built


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        publish_phase_hypotheses(
            resolved(args.phase_dir),
            resolved(args.output_dir),
            window_size=args.window_size,
            window_step=args.window_step,
            max_offset=args.max_offset,
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"OK phase-hypothesis research: {resolved(args.output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
