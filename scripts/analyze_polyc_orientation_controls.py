"""Build matched opposite-orientation controls for mtDNA poly-C research."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validation_corpus.polyc_orientation_controls import (
    publish_polyc_orientation_controls,
)

ROOT = Path(__file__).resolve().parents[1]


def resolved(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser(description=__doc__)
    built.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path("validation-results/corpus"),
        help="completed signal.validation_corpus/v1 directory",
    )
    built.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "validation-results/research/polyc-orientation-controls/baseline"
        ),
        help="new no-overwrite opposite-orientation control research directory",
    )
    return built


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        publish_polyc_orientation_controls(
            resolved(args.corpus_dir),
            resolved(args.output_dir),
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"OK poly-C orientation controls: {resolved(args.output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
