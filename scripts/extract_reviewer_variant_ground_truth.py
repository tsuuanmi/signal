"""Extract reviewer-produced Sequencher variant profiles into local proxy truth."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validation_corpus.reviewer_variants import extract_ground_truth

ROOT = Path(__file__).resolve().parents[1]


def resolved(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser(description=__doc__)
    built.add_argument("source_tsv", type=Path, help="reviewer comparison TSV")
    built.add_argument(
        "--output",
        type=Path,
        default=Path("data/validation/ground-truth/reviewer-variant-ground-truth.json"),
        help="new no-overwrite local proxy-ground-truth JSON",
    )
    return built


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        extract_ground_truth(resolved(args.source_tsv), resolved(args.output))
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"OK reviewer variant ground truth: {resolved(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
