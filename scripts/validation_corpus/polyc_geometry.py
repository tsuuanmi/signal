"""Shared rCRS poly-C read-path geometry for validation research."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

RCRS_LENGTH = 16_569


@dataclass(frozen=True)
class PolyCTract:
    tract_id: str
    start_1based: int
    end_1based: int
    interrupt_position_1based: int
    reference_sequence: str


@dataclass(frozen=True)
class TractCallSpan:
    first_call_index_0based: int
    last_call_index_0based: int


TRACTS = (
    PolyCTract("HV2_C", 303, 315, 310, "CCCCCCCTCCCCC"),
    PolyCTract("HV1_C", 16184, 16193, 16189, "CCCCCTCCCC"),
)


def orientation(value: object, label: str) -> str:
    if value not in {"forward", "reverse"}:
        raise ValueError(f"{label} must be forward or reverse")
    return str(value)


def tract_positions(tract: PolyCTract) -> range:
    return range(tract.start_1based, tract.end_1based + 1)


def covers_complete_tract(observed_positions: set[int], tract: PolyCTract) -> bool:
    return all(position in observed_positions for position in tract_positions(tract))


def validate_reference_tracts(
    reference_bases: Mapping[int, str],
) -> tuple[PolyCTract, ...]:
    active: list[PolyCTract] = []
    for tract in TRACTS:
        positions = tract_positions(tract)
        present = [position in reference_bases for position in positions]
        if not any(present):
            continue
        if not all(present):
            raise ValueError(
                f"{tract.tract_id}: validation corpus only partially represents "
                "the rCRS poly-C tract"
            )
        sequence = "".join(reference_bases[position] for position in positions)
        if sequence != tract.reference_sequence:
            raise ValueError(
                f"{tract.tract_id}: reference sequence {sequence!r} differs from "
                f"expected rCRS tract {tract.reference_sequence!r}"
            )
        active.append(tract)
    if not active:
        raise ValueError(
            "validation corpus contains no complete supported rCRS poly-C tract"
        )
    return tuple(active)


def tract_call_span(
    call_indices_by_position: Mapping[int, int | None],
    tract: PolyCTract,
    label: str,
) -> TractCallSpan:
    indices = [
        call_index
        for position in tract_positions(tract)
        if (call_index := call_indices_by_position.get(position)) is not None
    ]
    if not indices:
        raise ValueError(
            f"{label}: complete tract coverage has no call-backed tract observation"
        )
    if any(call_index < 0 for call_index in indices):
        raise ValueError(f"{label}: tract call indexes must be non-negative")
    return TractCallSpan(min(indices), max(indices))


def path_region(
    tract: PolyCTract,
    position_1based: int,
    call_index_0based: int | None,
    span: TractCallSpan,
) -> str:
    if tract.start_1based <= position_1based <= tract.end_1based:
        return "inside"
    if call_index_0based is None:
        return "unresolved"
    if call_index_0based < span.first_call_index_0based:
        return "before"
    if call_index_0based > span.last_call_index_0based:
        return "after"
    raise ValueError(
        f"{tract.tract_id}: outside-tract call {call_index_0based} lies within "
        "the tract call span"
    )


def oriented_reference_steps(
    start_1based: int,
    end_1based: int,
    selected_orientation: str,
) -> int:
    selected_orientation = orientation(selected_orientation, "orientation")
    for label, position in (
        ("start_1based", start_1based),
        ("end_1based", end_1based),
    ):
        if not 1 <= position <= RCRS_LENGTH:
            raise ValueError(f"{label} must be within rCRS")
    if selected_orientation == "forward":
        return (end_1based - start_1based) % RCRS_LENGTH
    return (start_1based - end_1based) % RCRS_LENGTH


def read_order_distance(
    tract: PolyCTract,
    selected_orientation: str,
    position_1based: int,
    region: str,
) -> int | None:
    selected_orientation = orientation(selected_orientation, "orientation")
    if region == "inside":
        return 0
    if region == "unresolved":
        return None
    if region not in {"before", "after"}:
        raise ValueError(f"unsupported path region {region!r}")

    if selected_orientation == "forward":
        entry = tract.start_1based
        exit_ = tract.end_1based
    else:
        entry = tract.end_1based
        exit_ = tract.start_1based

    if region == "after":
        distance = oriented_reference_steps(exit_, position_1based, selected_orientation)
        if distance <= 0:
            raise ValueError("after-tract reference distance must be positive")
        return distance

    distance = oriented_reference_steps(position_1based, entry, selected_orientation)
    if distance <= 0:
        raise ValueError("before-tract reference distance must be positive")
    return -distance


def call_distance(
    span: TractCallSpan,
    call_index_0based: int | None,
    region: str,
) -> int | None:
    if region == "inside":
        return 0
    if region == "unresolved" or call_index_0based is None:
        return None
    if region == "before":
        distance = call_index_0based - span.first_call_index_0based
        if distance >= 0:
            raise ValueError("before-tract call distance must be negative")
        return distance
    if region == "after":
        distance = call_index_0based - span.last_call_index_0based
        if distance <= 0:
            raise ValueError("after-tract call distance must be positive")
        return distance
    raise ValueError(f"unsupported path region {region!r}")


def wrapped_reference_position(position_1based: int) -> int:
    return (position_1based - 1) % RCRS_LENGTH + 1


def reference_neighbor_positions(
    selected_orientation: str,
    position_1based: int,
) -> tuple[int, int]:
    selected_orientation = orientation(selected_orientation, "orientation")
    if not 1 <= position_1based <= RCRS_LENGTH:
        raise ValueError("position_1based must be within rCRS")
    if selected_orientation == "forward":
        previous = wrapped_reference_position(position_1based - 1)
        next_ = wrapped_reference_position(position_1based + 1)
    else:
        previous = wrapped_reference_position(position_1based + 1)
        next_ = wrapped_reference_position(position_1based - 1)
    return previous, next_


__all__ = [
    "RCRS_LENGTH",
    "TRACTS",
    "PolyCTract",
    "TractCallSpan",
    "call_distance",
    "covers_complete_tract",
    "orientation",
    "path_region",
    "read_order_distance",
    "reference_neighbor_positions",
    "tract_call_span",
    "tract_positions",
    "validate_reference_tracts",
]
