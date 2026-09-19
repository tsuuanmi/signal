"""Build deterministic joined tables for local Signal validation research."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validation_corpus.research_runner import publish_research

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
        default=Path("validation-results/research/baseline"),
        help="new no-overwrite research dataset directory",
    )
    return built


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    corpus_dir = resolved(args.corpus_dir)
    output_dir = resolved(args.output_dir)
    try:
        publish_research(corpus_dir, output_dir)
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"OK validation research dataset: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
