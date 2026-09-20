"""Build descriptive post-poly-C phase-instability research tables."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validation_corpus.polyc_phase import publish_polyc_phase

ROOT = Path(__file__).resolve().parents[1]


def resolved(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser(description=__doc__)
    built.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path("validation-results/corpus"),
        help="completed validation corpus directory",
    )
    built.add_argument(
        "--output-dir",
        type=Path,
        default=Path("validation-results/research/polyc-phase/baseline"),
        help="new no-overwrite poly-C research directory",
    )
    return built


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    corpus_dir = resolved(args.corpus_dir)
    output_dir = resolved(args.output_dir)
    try:
        publish_polyc_phase(corpus_dir, output_dir)
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"OK poly-C phase research: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
