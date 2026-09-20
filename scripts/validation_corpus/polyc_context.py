"""Shared corpus-derived context for mtDNA poly-C validation research."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .polyc_geometry import (
    TRACTS,
    PolyCTract,
    TractCallSpan,
    covers_complete_tract,
    orientation,
    tract_call_span,
    tract_positions,
    validate_reference_tracts,
)
from .research_loader import iter_research_rows
from .research_model import ResearchCorpus


@dataclass
class ReadContext:
    validation_case_id: str
    source_group_id: str
    specimen_group_id: str | None
    read_sha256: str
    pcr_replicate_id: str | None
    sequencing_run_id: str | None
    instrument_id: str | None
    amplicon_id: str | None
    declared_direction: str | None
    artifact_tags: str
    orientation: str
    tract_positions: set[int] = field(default_factory=set)
    tract_call_indices: dict[int, int | None] = field(default_factory=dict)
    tract_observations: dict[int, dict[str, Any]] = field(default_factory=dict)


def optional_text(value: Any) -> str | None:
    return str(value) if value is not None else None


def profile(row: dict[str, Any]) -> tuple[float, float, float, float] | None:
    values = tuple(row[f"profile_{base}"] for base in ("a", "c", "g", "t"))
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise ValueError("profile channels must be all present or all absent")
    converted = tuple(float(value) for value in values)
    if any(not math.isfinite(value) or value < 0.0 for value in converted):
        raise ValueError("profile channels must be finite and non-negative")
    if abs(sum(converted) - 1.0) > 1e-9:
        raise ValueError("profile channels must sum to one")
    return converted[0], converted[1], converted[2], converted[3]


def mass_for_base(values: tuple[float, float, float, float], base: str) -> float:
    try:
        index = {"A": 0, "C": 1, "G": 2, "T": 3}[base]
    except KeyError as error:
        raise ValueError(f"unsupported reference base {base!r}") from error
    return values[index]


def scan_context(
    corpus: ResearchCorpus,
) -> tuple[dict[str, ReadContext], dict[int, str], tuple[PolyCTract, ...]]:
    contexts: dict[str, ReadContext] = {}
    reference_bases: dict[int, str] = {}
    supported_tract_positions = {
        position for tract in TRACTS for position in tract_positions(tract)
    }

    for locus_row, observation_rows in iter_research_rows(corpus):
        position = int(locus_row["position_1based"])
        reference_base = str(locus_row["reference_base"])
        previous = reference_bases.setdefault(position, reference_base)
        if previous != reference_base:
            raise ValueError(
                f"reference base at position {position} changes across validation cases"
            )

        for row in observation_rows:
            read_sha256 = str(row["read_sha256"])
            selected_orientation = orientation(
                row["orientation"],
                f"{read_sha256}.orientation",
            )
            context = contexts.get(read_sha256)
            if context is None:
                context = ReadContext(
                    validation_case_id=str(row["validation_case_id"]),
                    source_group_id=str(row["source_group_id"]),
                    specimen_group_id=optional_text(row["specimen_group_id"]),
                    read_sha256=read_sha256,
                    pcr_replicate_id=optional_text(row["pcr_replicate_id"]),
                    sequencing_run_id=optional_text(row["sequencing_run_id"]),
                    instrument_id=optional_text(row["instrument_id"]),
                    amplicon_id=optional_text(row["amplicon_id"]),
                    declared_direction=optional_text(row["declared_direction"]),
                    artifact_tags=str(row["artifact_tags"]),
                    orientation=selected_orientation,
                )
                contexts[read_sha256] = context
            else:
                if context.validation_case_id != row["validation_case_id"]:
                    raise ValueError(
                        f"{read_sha256}: validation case changes across rows"
                    )
                if context.orientation != selected_orientation:
                    raise ValueError(
                        f"{read_sha256}: selected orientation changes across rows"
                    )

            if position in supported_tract_positions:
                if position in context.tract_observations:
                    raise ValueError(
                        f"{read_sha256}: duplicate observation at position {position}"
                    )
                context.tract_positions.add(position)
                call_index = row["call_index_0based"]
                context.tract_call_indices[position] = (
                    int(call_index) if call_index is not None else None
                )
                context.tract_observations[position] = row

    return contexts, reference_bases, validate_reference_tracts(reference_bases)


def crossing_spans(
    contexts: dict[str, ReadContext],
    active_tracts: tuple[PolyCTract, ...],
) -> dict[tuple[str, str], TractCallSpan]:
    return {
        (read_sha256, tract.tract_id): tract_call_span(
            context.tract_call_indices,
            tract,
            f"{read_sha256}:{tract.tract_id}",
        )
        for read_sha256, context in contexts.items()
        for tract in active_tracts
        if covers_complete_tract(context.tract_positions, tract)
    }


__all__ = [
    "ReadContext",
    "crossing_spans",
    "mass_for_base",
    "profile",
    "scan_context",
]
