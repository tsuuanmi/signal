"""Strict loading and joining of validation corpus research data."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from collections.abc import Iterator
from typing import Any

from .measurements import load_measurements
from .model import (
    CORPUS_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    MEASUREMENT_SCHEMA_VERSION,
)
from .research_model import (
    CASE_FIELDS,
    LOCUS_FIELDS,
    OBSERVATION_FIELDS,
    READ_FIELDS,
    ResearchCase,
    ResearchCorpus,
)

SHA256 = re.compile(r"^[0-9a-f]{64}$")
INDEX_FIELDS = (
    "schema_version",
    "manifest_schema_version",
    "measurement_schema_version",
    "signal_version",
    "manifest_sha256",
    "reference_sha256",
    "configuration_sha256",
    "case_count",
    "trace_count",
    "cases",
)
CASE_INDEX_FIELDS = (*CASE_FIELDS, "measurement_file", "loci", "reads")
LOCUS_INTEGER_FIELDS = (
    "position_1based",
    "reads",
    "forward_reads",
    "reverse_reads",
    "reference_reads",
    "alternate_reads",
    "unresolved_reads",
    "deletion_reads",
    "profile_reads",
    "profile_forward_reads",
    "profile_reverse_reads",
    "contributors",
    "forward_contributors",
    "reverse_contributors",
    "noisy_observations",
    "missing_profile_observations",
    "deletion_observations",
)
LOCUS_OPTIONAL_NUMERIC_FIELDS = (
    "mean_a",
    "mean_c",
    "mean_g",
    "mean_t",
    "within_profile_impurity",
    "between_profile_dispersion",
    "total_profile_heterogeneity",
    "forward_within_profile_impurity",
    "forward_between_profile_dispersion",
    "forward_total_profile_heterogeneity",
    "reverse_within_profile_impurity",
    "reverse_between_profile_dispersion",
    "reverse_total_profile_heterogeneity",
    "directional_profile_distance",
)
OBSERVATION_OPTIONAL_INTEGER_FIELDS = (
    "quality",
    "call_index_0based",
    "ploc_0based",
    "window_start_0based",
    "window_end_0based_exclusive",
    "primary_peak_position_0based",
    "primary_peak_offset_from_ploc",
    "event_position_0based",
    "event_offset_from_ploc",
    "event_offset_from_primary_peak",
)


def strict_keys(value: dict[str, Any], expected: tuple[str, ...], label: str) -> None:
    missing = sorted(set(expected) - set(value))
    extra = sorted(set(value) - set(expected))
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if extra:
            details.append(f"unexpected: {', '.join(extra)}")
        raise ValueError(f"{label} fields are invalid: {'; '.join(details)}")


def required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise TypeError(f"{label} must be a non-empty string")
    return value


def optional_string(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string or null")
    return value


def required_integer(value: Any, label: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise TypeError(f"{label} must be an integer >= {minimum}")
    return value


def optional_integer(value: Any, label: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{label} must be an integer or null")
    return value


def optional_number(value: Any, label: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"{label} must be numeric or null")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{label} must be finite")
    return converted


def sha256_string(value: Any, label: str) -> str:
    text = required_string(value, label)
    if SHA256.fullmatch(text) is None:
        raise ValueError(f"{label} must be 64 lowercase hex characters")
    return text


def json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}: invalid JSON: {error.msg}") from error
    if not isinstance(value, dict):
        raise TypeError(f"{path}: expected a JSON object")
    return value


def case_metadata(record: dict[str, Any], label: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "validation_case_id": required_string(
            record["validation_case_id"], f"{label}.validation_case_id"
        ),
        "source_group_id": required_string(
            record["source_group_id"], f"{label}.source_group_id"
        ),
        "specimen_group_id": optional_string(
            record["specimen_group_id"], f"{label}.specimen_group_id"
        ),
        "truth_class": required_string(record["truth_class"], f"{label}.truth_class"),
        "truth_method": required_string(
            record["truth_method"], f"{label}.truth_method"
        ),
        "truth_locus": optional_integer(record["truth_locus"], f"{label}.truth_locus"),
        "truth_reference": optional_string(
            record["truth_reference"], f"{label}.truth_reference"
        ),
        "truth_alternate": optional_string(
            record["truth_alternate"], f"{label}.truth_alternate"
        ),
        "known_mixture_fraction": optional_number(
            record["known_mixture_fraction"], f"{label}.known_mixture_fraction"
        ),
        "holdout_group": required_string(
            record["holdout_group"], f"{label}.holdout_group"
        ),
        "approval_record": required_string(
            record["approval_record"], f"{label}.approval_record"
        ),
        "redistribution_status": required_string(
            record["redistribution_status"], f"{label}.redistribution_status"
        ),
        "notes": optional_string(record["notes"], f"{label}.notes"),
    }
    fit = record["include_in_threshold_fit"]
    if not isinstance(fit, bool):
        raise TypeError(f"{label}.include_in_threshold_fit must be boolean")
    metadata["include_in_threshold_fit"] = fit
    fraction = metadata["known_mixture_fraction"]
    if fraction is not None and not 0.0 <= fraction <= 1.0:
        raise ValueError(f"{label}.known_mixture_fraction must be within [0, 1]")
    truth_locus = metadata["truth_locus"]
    if truth_locus is not None and truth_locus < 1:
        raise ValueError(f"{label}.truth_locus must be at least 1")
    return metadata


def read_metadata(record: Any, label: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise TypeError(f"{label} must be an object")
    strict_keys(record, READ_FIELDS, label)
    artifact_tags = record["artifact_tags"]
    if not isinstance(artifact_tags, list) or not all(
        isinstance(tag, str) and tag for tag in artifact_tags
    ):
        raise TypeError(f"{label}.artifact_tags must be an array of non-empty strings")
    if len(artifact_tags) != len(set(artifact_tags)):
        raise ValueError(f"{label}.artifact_tags must be unique")
    direction = optional_string(record["declared_direction"], f"{label}.declared_direction")
    if direction not in {None, "forward", "reverse"}:
        raise ValueError(f"{label}.declared_direction is invalid")
    return {
        "trace_sha256": sha256_string(
            record["trace_sha256"], f"{label}.trace_sha256"
        ),
        "pcr_replicate_id": optional_string(
            record["pcr_replicate_id"], f"{label}.pcr_replicate_id"
        ),
        "sequencing_run_id": optional_string(
            record["sequencing_run_id"], f"{label}.sequencing_run_id"
        ),
        "instrument_id": optional_string(
            record["instrument_id"], f"{label}.instrument_id"
        ),
        "amplicon_id": optional_string(record["amplicon_id"], f"{label}.amplicon_id"),
        "declared_direction": direction,
        "artifact_tags": tuple(artifact_tags),
    }


def load_research_corpus(corpus_dir: Path) -> ResearchCorpus:
    root = corpus_dir.resolve()
    index_path = root / "index.json"
    if not index_path.is_file():
        raise ValueError(f"corpus index is not a regular file: {index_path}")
    index = json_object(index_path)
    strict_keys(index, INDEX_FIELDS, "corpus index")
    if index["schema_version"] != CORPUS_SCHEMA_VERSION:
        raise ValueError(f"unsupported corpus schema: {index['schema_version']!r}")
    if index["manifest_schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported manifest schema: {index['manifest_schema_version']!r}"
        )
    if index["measurement_schema_version"] != MEASUREMENT_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported measurement schema: {index['measurement_schema_version']!r}"
        )

    signal_version = required_string(index["signal_version"], "signal_version")
    manifest_sha256 = sha256_string(index["manifest_sha256"], "manifest_sha256")
    reference_sha256 = sha256_string(index["reference_sha256"], "reference_sha256")
    configuration_sha256 = sha256_string(
        index["configuration_sha256"], "configuration_sha256"
    )
    case_count = required_integer(index["case_count"], "case_count", 1)
    trace_count = required_integer(index["trace_count"], "trace_count", 1)
    raw_cases = index["cases"]
    if not isinstance(raw_cases, list):
        raise TypeError("corpus index cases must be an array")
    if len(raw_cases) != case_count:
        raise ValueError("corpus index case_count does not match cases[]")

    cases: list[ResearchCase] = []
    global_reads: set[str] = set()
    source_holdouts: dict[str, str] = {}
    observed_trace_count = 0
    for case_index, raw_case in enumerate(raw_cases):
        label = f"cases[{case_index}]"
        if not isinstance(raw_case, dict):
            raise TypeError(f"{label} must be an object")
        strict_keys(raw_case, CASE_INDEX_FIELDS, label)
        metadata = case_metadata(raw_case, label)
        case_id = metadata["validation_case_id"]
        expected_file = f"cases/{case_id}.jsonl"
        measurement_file = required_string(
            raw_case["measurement_file"], f"{label}.measurement_file"
        )
        if measurement_file != expected_file:
            raise ValueError(
                f"{label}.measurement_file must be exactly {expected_file!r}"
            )
        loci = required_integer(raw_case["loci"], f"{label}.loci", 1)
        raw_reads = raw_case["reads"]
        if not isinstance(raw_reads, list) or not raw_reads:
            raise TypeError(f"{label}.reads must be a non-empty array")

        reads: dict[str, dict[str, Any]] = {}
        for read_index, raw_read in enumerate(raw_reads):
            read = read_metadata(raw_read, f"{label}.reads[{read_index}]")
            read_sha256 = read["trace_sha256"]
            if read_sha256 in reads or read_sha256 in global_reads:
                raise ValueError(f"duplicate trace SHA-256 in corpus index: {read_sha256}")
            reads[read_sha256] = read
            global_reads.add(read_sha256)
        observed_trace_count += len(reads)

        source_group_id = metadata["source_group_id"]
        holdout_group = metadata["holdout_group"]
        previous_holdout = source_holdouts.setdefault(source_group_id, holdout_group)
        if previous_holdout != holdout_group:
            raise ValueError(
                f"source_group_id {source_group_id!r} spans holdout groups "
                f"{previous_holdout!r} and {holdout_group!r}"
            )

        cases.append(
            ResearchCase(
                metadata=metadata,
                measurement_file=root / expected_file,
                loci=loci,
                reads=reads,
            )
        )

    if observed_trace_count != trace_count:
        raise ValueError("corpus index trace_count does not match reads[]")
    return ResearchCorpus(
        index_path=index_path,
        signal_version=signal_version,
        manifest_sha256=manifest_sha256,
        reference_sha256=reference_sha256,
        configuration_sha256=configuration_sha256,
        cases=cases,
    )


def validate_locus_row(row: dict[str, Any], label: str) -> None:
    strict_keys(row, LOCUS_FIELDS, label)
    reference_base = required_string(row["reference_base"], f"{label}.reference_base")
    if len(reference_base) != 1:
        raise ValueError(f"{label}.reference_base must contain one nucleotide")
    for field in LOCUS_INTEGER_FIELDS:
        minimum = 1 if field == "position_1based" else 0
        required_integer(row[field], f"{label}.{field}", minimum)
    for field in LOCUS_OPTIONAL_NUMERIC_FIELDS:
        optional_number(row[field], f"{label}.{field}")


def four_values(
    value: Any,
    label: str,
    expected_type: type[int] | type[str] | type[float],
) -> tuple[Any, Any, Any, Any] | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 4:
        raise TypeError(f"{label} must be a four-element array or null")
    converted: list[Any] = []
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if expected_type is int:
            if not isinstance(item, int) or isinstance(item, bool):
                raise TypeError(f"{item_label} must be an integer")
            converted.append(item)
        elif expected_type is str:
            converted.append(required_string(item, item_label))
        else:
            number = optional_number(item, item_label)
            if number is None:
                raise TypeError(f"{item_label} must be numeric")
            converted.append(number)
    return (converted[0], converted[1], converted[2], converted[3])


def validate_observation(observation: Any, label: str) -> dict[str, Any]:
    if not isinstance(observation, dict):
        raise TypeError(f"{label} must be an object")
    strict_keys(observation, OBSERVATION_FIELDS, label)
    required_string(observation["read_sha256"], f"{label}.read_sha256")
    required_string(observation["orientation"], f"{label}.orientation")
    required_string(observation["state"], f"{label}.state")
    for field in ("aligned_base", "source_primary", "source_ambiguity"):
        optional_string(observation[field], f"{label}.{field}")
    for field in OBSERVATION_OPTIONAL_INTEGER_FIELDS:
        optional_integer(observation[field], f"{label}.{field}")
    noisy = observation["in_noisy_region"]
    if noisy is not None and not isinstance(noisy, bool):
        raise TypeError(f"{label}.in_noisy_region must be boolean or null")

    positions = four_values(
        observation["channel_peak_positions_acgt_reference"],
        f"{label}.channel_peak_positions_acgt_reference",
        int,
    )
    if positions is not None and any(position < 0 for position in positions):
        raise ValueError(
            f"{label}.channel_peak_positions_acgt_reference must be non-negative"
        )
    four_values(
        observation["channel_peak_heights_acgt_reference"],
        f"{label}.channel_peak_heights_acgt_reference",
        int,
    )
    four_values(
        observation["channel_peak_sources_acgt_reference"],
        f"{label}.channel_peak_sources_acgt_reference",
        str,
    )
    four_values(
        observation["primary_peak_heights_acgt_reference"],
        f"{label}.primary_peak_heights_acgt_reference",
        int,
    )
    four_values(
        observation["corrected_amplitudes_acgt_reference"],
        f"{label}.corrected_amplitudes_acgt_reference",
        float,
    )
    four_values(
        observation["snrs_acgt_reference"],
        f"{label}.snrs_acgt_reference",
        float,
    )
    four_values(
        observation["profile_acgt_reference"],
        f"{label}.profile_acgt_reference",
        float,
    )
    return observation


def truth_locus(metadata: dict[str, Any], position: int) -> bool:
    expected = metadata["truth_locus"]
    return expected is not None and expected == position


def flatten_channels(
    target: dict[str, Any],
    prefix: str,
    values: tuple[Any, Any, Any, Any] | None,
) -> None:
    for suffix, value in zip(("a", "c", "g", "t"), values or (None,) * 4, strict=True):
        target[f"{prefix}_{suffix}"] = value


def iter_research_rows(
    corpus: ResearchCorpus,
) -> Iterator[tuple[dict[str, Any], list[dict[str, Any]]]]:
    """Yield one joined locus row plus its joined observation rows at a time."""
    for case in corpus.cases:
        case_id = case.metadata["validation_case_id"]
        validated = load_measurements(
            case.measurement_file, case_id, set(case.reads)
        )
        summary = validated.summary
        if summary.signal_version != corpus.signal_version:
            raise ValueError(f"{case_id}: Signal version differs from corpus index")
        if summary.reference_sha256 != corpus.reference_sha256:
            raise ValueError(f"{case_id}: reference SHA-256 differs from corpus index")
        if summary.configuration_sha256 != corpus.configuration_sha256:
            raise ValueError(
                f"{case_id}: configuration SHA-256 differs from corpus index"
            )
        if summary.loci != case.loci:
            raise ValueError(f"{case_id}: locus count differs from corpus index")

        for locus_index, row in enumerate(validated.rows):
            label = f"{case_id}.loci[{locus_index}]"
            validate_locus_row(row, label)
            position = required_integer(
                row["position_1based"], f"{label}.position_1based", 1
            )
            is_truth_locus = truth_locus(case.metadata, position)
            locus_row = dict(case.metadata)
            locus_row["is_truth_locus"] = is_truth_locus
            for field in LOCUS_FIELDS[:-1]:
                locus_row[field] = row[field]

            joined_observations: list[dict[str, Any]] = []
            raw_observations = row["observations"]
            if not isinstance(raw_observations, list):
                raise TypeError(f"{label}.observations must be an array")
            for observation_index, raw_observation in enumerate(raw_observations):
                observation = validate_observation(
                    raw_observation, f"{label}.observations[{observation_index}]"
                )
                read_sha256 = observation["read_sha256"]
                if not isinstance(read_sha256, str) or read_sha256 not in case.reads:
                    raise ValueError(f"{label}: observation references unknown read")
                read = case.reads[read_sha256]

                output = dict(case.metadata)
                output.update(
                    {
                        "is_truth_locus": is_truth_locus,
                        "position_1based": position,
                        "reference_base": row["reference_base"],
                        "read_sha256": read_sha256,
                        "pcr_replicate_id": read["pcr_replicate_id"],
                        "sequencing_run_id": read["sequencing_run_id"],
                        "instrument_id": read["instrument_id"],
                        "amplicon_id": read["amplicon_id"],
                        "declared_direction": read["declared_direction"],
                        "artifact_tags": ";".join(read["artifact_tags"]),
                    }
                )
                for field in OBSERVATION_FIELDS:
                    if field not in {
                        "read_sha256",
                        "channel_peak_positions_acgt_reference",
                        "channel_peak_heights_acgt_reference",
                        "channel_peak_sources_acgt_reference",
                        "primary_peak_heights_acgt_reference",
                        "corrected_amplitudes_acgt_reference",
                        "snrs_acgt_reference",
                        "profile_acgt_reference",
                    }:
                        output[field] = observation[field]

                flatten_channels(
                    output,
                    "channel_peak_position",
                    four_values(
                        observation["channel_peak_positions_acgt_reference"],
                        f"{label}.channel_peak_positions_acgt_reference",
                        int,
                    ),
                )
                flatten_channels(
                    output,
                    "channel_peak_height",
                    four_values(
                        observation["channel_peak_heights_acgt_reference"],
                        f"{label}.channel_peak_heights_acgt_reference",
                        int,
                    ),
                )
                flatten_channels(
                    output,
                    "channel_peak_source",
                    four_values(
                        observation["channel_peak_sources_acgt_reference"],
                        f"{label}.channel_peak_sources_acgt_reference",
                        str,
                    ),
                )
                flatten_channels(
                    output,
                    "primary_peak_height",
                    four_values(
                        observation["primary_peak_heights_acgt_reference"],
                        f"{label}.primary_peak_heights_acgt_reference",
                        int,
                    ),
                )
                flatten_channels(
                    output,
                    "corrected_amplitude",
                    four_values(
                        observation["corrected_amplitudes_acgt_reference"],
                        f"{label}.corrected_amplitudes_acgt_reference",
                        float,
                    ),
                )
                flatten_channels(
                    output,
                    "snr",
                    four_values(
                        observation["snrs_acgt_reference"],
                        f"{label}.snrs_acgt_reference",
                        float,
                    ),
                )
                flatten_channels(
                    output,
                    "profile",
                    four_values(
                        observation["profile_acgt_reference"],
                        f"{label}.profile_acgt_reference",
                        float,
                    ),
                )
                joined_observations.append(output)

            yield locus_row, joined_observations
