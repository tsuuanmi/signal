"""Characterize development phase evidence around biological disagreements."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validation_corpus.phase_error_characterization import (
    publish_phase_error_characterization,
)

ROOT = Path(__file__).resolve().parents[1]


def resolved(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser(description=__doc__)
    built.add_argument(
        "--interpretation-dir",
        type=Path,
        default=Path(
            "validation-results/research/phase-interpretation-dataset/baseline"
        ),
        help="completed signal.validation_phase_interpretation_dataset/v1 directory",
    )
    built.add_argument(
        "--context-dir",
        type=Path,
        default=Path(
            "validation-results/research/variant-phase-context/baseline"
        ),
        help="completed signal.validation_variant_phase_context/v1 directory",
    )
    built.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "validation-results/research/phase-error-characterization/baseline"
        ),
        help="new no-overwrite signal.validation_phase_error_characterization/v1 directory",
    )
    return built


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        publish_phase_error_characterization(
            resolved(args.interpretation_dir),
            resolved(args.context_dir),
            resolved(args.output_dir),
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"OK phase error characterization: {resolved(args.output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
