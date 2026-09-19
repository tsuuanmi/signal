"""Streaming descriptive statistics for validation research datasets."""

from __future__ import annotations

import math
from array import array
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from .research_model import METRICS


def numeric_value(value: Any, label: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"{label} must be numeric or null")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{label} must be finite")
    return converted


def nearest_rank(values: Sequence[float], probability: float) -> float:
    """Return an empirical nearest-rank quantile without interpolation."""
    if not values:
        raise ValueError("cannot calculate a quantile from an empty sample")
    if not 0.0 < probability <= 1.0:
        raise ValueError("probability must be within (0, 1]")
    ordered = sorted(values)
    rank = max(1, math.ceil(probability * len(ordered)))
    return ordered[rank - 1]


@dataclass
class GroupAccumulator:
    case_ids: set[str] = field(default_factory=set)
    source_groups: set[str] = field(default_factory=set)
    loci: int = 0
    observations: int = 0
    values: dict[str, array[float]] = field(
        default_factory=lambda: {metric: array("d") for metric in METRICS}
    )
    missing: dict[str, int] = field(
        default_factory=lambda: {metric: 0 for metric in METRICS}
    )

    def add(self, row: dict[str, Any]) -> None:
        case_id = row.get("validation_case_id")
        source_group = row.get("source_group_id")
        reads = row.get("reads")
        if not isinstance(case_id, str) or not case_id:
            raise TypeError("validation_case_id must be a non-empty string")
        if not isinstance(source_group, str) or not source_group:
            raise TypeError("source_group_id must be a non-empty string")
        if not isinstance(reads, int) or isinstance(reads, bool) or reads < 0:
            raise TypeError("reads must be a non-negative integer")

        self.case_ids.add(case_id)
        self.source_groups.add(source_group)
        self.loci += 1
        self.observations += reads
        for metric in METRICS:
            value = numeric_value(row.get(metric), metric)
            if value is None:
                self.missing[metric] += 1
            else:
                self.values[metric].append(value)


def metric_summary(
    groups: Sequence[GroupAccumulator], metric: str
) -> dict[str, Any]:
    values = array("d")
    missing = 0
    for group in groups:
        values.extend(group.values[metric])
        missing += group.missing[metric]
    if not values:
        return {"n": 0, "missing": missing}

    return {
        "n": len(values),
        "missing": missing,
        "min": min(values),
        "mean": math.fsum(values) / len(values),
        "p50": nearest_rank(values, 0.50),
        "p90": nearest_rank(values, 0.90),
        "p95": nearest_rank(values, 0.95),
        "p99": nearest_rank(values, 0.99),
        "max": max(values),
    }


def group_summary(groups: Sequence[GroupAccumulator]) -> dict[str, Any]:
    case_ids: set[str] = set()
    source_groups: set[str] = set()
    loci = 0
    observations = 0
    for group in groups:
        case_ids.update(group.case_ids)
        source_groups.update(group.source_groups)
        loci += group.loci
        observations += group.observations
    return {
        "cases": len(case_ids),
        "source_groups": len(source_groups),
        "loci": loci,
        "observations": observations,
        "metrics": {metric: metric_summary(groups, metric) for metric in METRICS},
    }


class ResearchStatisticsAccumulator:
    """Accumulate exact metric distributions without retaining joined row objects."""

    def __init__(self) -> None:
        self._groups: dict[tuple[str, str, bool], GroupAccumulator] = {}

    def add(self, row: dict[str, Any]) -> None:
        holdout_group = row.get("holdout_group")
        truth_class = row.get("truth_class")
        include = row.get("include_in_threshold_fit")
        if not isinstance(holdout_group, str) or not holdout_group:
            raise TypeError("holdout_group must be a non-empty string")
        if not isinstance(truth_class, str) or not truth_class:
            raise TypeError("truth_class must be a non-empty string")
        if not isinstance(include, bool):
            raise TypeError("include_in_threshold_fit must be boolean")

        key = (holdout_group, truth_class, include)
        self._groups.setdefault(key, GroupAccumulator()).add(row)

    def result(self) -> dict[str, Any]:
        ordered = sorted(self._groups.items())
        groups = [group for _, group in ordered]
        fit_groups = [group for (key, group) in ordered if key[2]]
        grouped: list[dict[str, Any]] = []
        for (holdout_group, truth_class, include), group in ordered:
            record: dict[str, Any] = {
                "holdout_group": holdout_group,
                "truth_class": truth_class,
                "include_in_threshold_fit": include,
            }
            record.update(group_summary([group]))
            grouped.append(record)
        return {
            "quantile_method": "empirical_nearest_rank",
            "metrics": list(METRICS),
            "overall": group_summary(groups),
            "threshold_fit_only": group_summary(fit_groups),
            "groups": grouped,
        }
