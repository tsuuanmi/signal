"""Join biological variant-profile disagreements to exact phase evidence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validation_corpus.phase_interpretation_dataset import PartitionPlan
from validation_corpus.variant_phase_context import publish_variant_phase_context

ROOT = Path(__file__).resolve().parents[1]


def resolved(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser(description=__doc__)
    built.add_argument(
        "--evaluation-dir",
        type=Path,
        default=Path("validation-results/variant-profile/baseline"),
        help="completed signal.validation_variant_profile_evaluation/v2 directory",
    )
    built.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path("validation-results/corpus"),
        help="completed signal.validation_corpus/v1 directory",
    )
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
        default=Path("validation-results/research/variant-phase-context/baseline"),
        help="new no-overwrite signal.validation_variant_phase_context/v1 directory",
    )
    built.add_argument(
        "--development-group",
        action="append",
        required=True,
        help="holdout_group admitted to detailed development attribution; repeat as needed",
    )
    built.add_argument(
        "--holdout-group",
        action="append",
        required=True,
        help="locked holdout holdout_group; repeat as needed",
    )
    built.add_argument(
        "--excluded-group",
        action="append",
        default=[],
        help="holdout_group explicitly excluded from this study",
    )
    built.add_argument(
        "--unassigned-group",
        action="append",
        default=[],
        help="holdout_group explicitly marked unassigned",
    )
    return built


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    plan = PartitionPlan(
        development=tuple(args.development_group),
        holdout=tuple(args.holdout_group),
        excluded=tuple(args.excluded_group),
        unassigned=tuple(args.unassigned_group),
    )
    try:
        publish_variant_phase_context(
            resolved(args.evaluation_dir),
            resolved(args.corpus_dir),
            resolved(args.phase_dir),
            resolved(args.hypotheses_dir),
            resolved(args.output_dir),
            plan,
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"OK variant phase context: {resolved(args.output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
