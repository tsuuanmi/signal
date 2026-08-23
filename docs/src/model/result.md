# `src/model/result.rs`

## Purpose

Defines the compact serializable `signal.analysis/v4` document contract.

## Responsibilities

- Represent the selected run identity, sequence, signal annotations, alignment,
  reported variants, and a compact warning summary.
- Provide the typed structs that `report::json` serializes deterministically.
- Omit decoded bulk data, per-call tables, losing orientation candidates, and the
  complete reference/configuration, which remain internal to the algorithms.

## Non-responsibilities

No serialization logic, filesystem access, or algorithm execution.

## Key types and functions

- `AnalysisResult`: `schema_version`, `meta`, `sequence`, `signal`, `alignment`,
  `variants`,
  and `warnings`.
- `MetaResult` with `TraceResult` (input identity), `ReferenceResult`,
  `MethodsResult` (versioned method IDs, including `signal.peak_recall/v2`,
  `signal.windowed_snr/v1`, and `signal.primary_difference/v3`), and
  `configuration_sha256`.
- `SequenceResult`: primary, ambiguity, retained sequence, and trim interval.
- `SignalResult`, `SignalWindowResult`, and `NoisyRegionResult`: bounded rolling
  SNR features and merged call/sample intervals.
- `AlignmentResult`: the selected alignment only — orientation, score, metrics,
  `reference_segments`, `wraps_origin`, `operation_runs`, and gapped rows.
- `VariantResult` with a `calls` vector of `VariantCallResult` for each
  supporting/flanking call. Field names are concise (`position`, `reference`,
  `alternate`, `kind`) rather than verbose descriptors.
- `VariantCallResult`: role, 0-based call `index`, optional one-based reference
  `position` (absent for inserted calls), the 0-based `ploc`, primary and
  ambiguity symbols, `ChannelPeaksResult`, and `VariantQualityResult`.
- `ChannelPeaksResult` and `PeakResult`: one A/C/G/T peak (height, 0-based
  trace position, and selection `source`) per variant-associated call.
- `VariantQualityResult`: relative score, penalty, calibration flag, and optional
  vendor score plus applicability.
- `WarningSummaryResult`: compact counts of non-fatal conditions plus the
  boolean `reference_origin_wrap` flag.

## Invariants and errors

- `schema_version` is `signal.analysis/v4`.
- Call `position` is skipped for inserted calls; `vendor_score` is skipped when
  the ABIF input has no PCON value.
- The document is deterministic: identical inputs produce identical output.
- Only the selected alignment and direct variant-associated calls are emitted;
  dead and duplicate fields are absent.

## Dependencies

- `model::alignment` (`AlignmentMetrics`, `Orientation`).
- `model::basecalls` (`PeakSource`).
- `model::reference` (`ReferenceTopology`).
- `model::variant` (`VariantCallRole`, `VariantKind`).
- `serde` for serialization.

## Biological semantics

The result document records the selected sequence, the retained trim interval,
the winning alignment, and the reported variants with the direct original-call
evidence (trace PLOC and channel peak positions are 0-based sample coordinates;
the reported variant reference position is 1-based). Non-variant positions carry
no per-call peaks or quality in the output. Provenance and configuration identity
are included for reproducibility.

## Tests

No dedicated unit tests; the schema is exercised through `report::json`,
`report::variant`, and the integration tests.

## Status

Implemented.
