"""Summarize threshold-free explainability of post-poly-C candidate curves."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validation_corpus.phase_explainability import publish_phase_explainability

ROOT = Path(__file__).resolve().parents[1]


def resolved(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser(description=__doc__)
    built.add_argument(
        "--hypotheses-dir",
        type=Path,
        default=Path("validation-results/research/polyc-phase-hypotheses/baseline"),
        help="completed signal.validation_phase_hypotheses/v1 directory",
    )
    built.add_argument(
        "--output-dir",
        type=Path,
        default=Path("validation-results/research/polyc-phase-explainability/baseline"),
        help="new no-overwrite phase-explainability research directory",
    )
    return built


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        publish_phase_explainability(
            resolved(args.hypotheses_dir),
            resolved(args.output_dir),
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"OK phase-explainability research: {resolved(args.output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
