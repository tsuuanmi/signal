"""Filesystem primitives for deterministic validation-corpus publication."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def validate_new_directory(path: Path, protected: tuple[Path, ...]) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError(f"output directory already exists: {path}")
    for protected_path in protected:
        if paths_overlap(path, protected_path):
            raise ValueError(
                f"output directory overlaps protected input: {protected_path}"
            )


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_bytes(path: Path, content: bytes) -> None:
    with path.open("xb") as target:
        target.write(content)
        target.flush()
        os.fsync(target.fileno())


def write_json(path: Path, value: dict[str, Any]) -> None:
    encoded = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    write_bytes(path, encoded)
