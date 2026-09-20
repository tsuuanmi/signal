"""Compare current Signal sample variants with reviewer-derived proxy truth."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validation_corpus.variant_profile_evaluation import publish_evaluation

ROOT = Path(__file__).resolve().parents[1]


def resolved(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser(description=__doc__)
    built.add_argument(
        "--ground-truth",
        type=Path,
        default=Path(
            "data/validation/ground-truth/reviewer-variant-ground-truth.json"
        ),
        help="reviewer-derived proxy-ground-truth JSON",
    )
    built.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="Signal batch result root containing <case>/<case>.json",
    )
    built.add_argument(
        "--reference",
        type=Path,
        default=Path("references/rCRS.fasta"),
        help="reference FASTA used by Signal results",
    )
    built.add_argument(
        "--output-dir",
        type=Path,
        default=Path("validation-results/variant-profile/baseline"),
        help="new no-overwrite evaluation directory",
    )
    return built


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        publish_evaluation(
            resolved(args.ground_truth),
            resolved(args.results_dir),
            resolved(args.reference),
            resolved(args.output_dir),
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"OK variant-profile evaluation: {resolved(args.output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
