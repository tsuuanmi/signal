"""Join recurrent mtDNA loci to exact post-poly-C phase-window context."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validation_corpus.phase_recurrent_loci import publish_phase_recurrent_loci

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
        "--hypotheses-dir",
        type=Path,
        default=Path("validation-results/research/polyc-phase-hypotheses/baseline"),
        help="completed signal.validation_phase_hypotheses/v1 directory",
    )
    built.add_argument(
        "--output-dir",
        type=Path,
        default=Path("validation-results/research/polyc-phase-recurrent-loci/baseline"),
        help="new no-overwrite recurrent-locus research directory",
    )
    return built


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        publish_phase_recurrent_loci(
            resolved(args.phase_dir),
            resolved(args.hypotheses_dir),
            resolved(args.output_dir),
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"OK recurrent-locus phase research: {resolved(args.output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
