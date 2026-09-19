"""Prepare an immutable validation curation queue and editable decisions template."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validation_corpus.curation import publish_curation_queue

ROOT = Path(__file__).resolve().parents[1]


def resolved(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def parser() -> argparse.ArgumentParser:
    built = argparse.ArgumentParser(description=__doc__)
    built.add_argument(
        "--audit-dir",
        type=Path,
        default=Path("validation-results/audit/baseline"),
        help="completed validation audit directory",
    )
    built.add_argument(
        "--output-dir",
        type=Path,
        default=Path("validation-results/curation/baseline"),
        help="new no-overwrite curation queue directory",
    )
    return built


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    output_dir = resolved(args.output_dir)
    try:
        publish_curation_queue(resolved(args.audit_dir), output_dir)
    except (OSError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"OK validation curation queue: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
