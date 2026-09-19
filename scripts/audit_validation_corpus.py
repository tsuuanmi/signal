"""Build deterministic observational validation audit strata."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validation_corpus.audit_runner import publish_audit

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
        "--research-dir",
        type=Path,
        default=Path("validation-results/research/baseline"),
        help="completed validation research dataset directory",
    )
    built.add_argument(
        "--output-dir",
        type=Path,
        default=Path("validation-results/audit/baseline"),
        help="new no-overwrite validation audit directory",
    )
    return built


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        publish_audit(
            resolved(args.corpus_dir),
            resolved(args.research_dir),
            resolved(args.output_dir),
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"OK validation audit: {resolved(args.output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
