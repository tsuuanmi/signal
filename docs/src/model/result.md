# `src/model/result.rs`

## Purpose

Defines the compact serializable `signal.analysis/v5` document contract.

## Responsibilities

- Represent deterministic provenance, the read extent, merged signal-quality
  regions, a concise selected-alignment summary, reported variants with essential
  supporting evidence, and public warning counts.
- Provide the typed structs that `report::json` serializes deterministically.
- Keep bulk sequences, full channel arrays, per-call tables, detailed alignments,
  vendor-only evidence, and operational-only warning categories out of JSON.

## Non-responsibilities

No serialization logic, filesystem access, scientific computation, or variant
projection.

## Key types and functions

- `AnalysisResult`: `schema_version`, `provenance`, `read`, `signal_quality`,
  `alignment`, `variants`, and `warnings`.
- `ProvenanceResult`: software version, input SHA-256, reference identity, and
  configuration SHA-256. `InputResult` deliberately omits the trace filename;
  `ReferenceResult` carries name, topology, and sequence SHA-256.
- `ReadResult`: total `call_count` and the retained 0-based half-open `trim`
  interval. Complete called and retained sequences are not serialized.
- `SignalQualityResult`: only merged `noisy_regions`. Each `NoisyRegionResult`
  contains call/sample intervals and the minimum primary SNR; individual rolling
  windows and maximum secondary SNR are not serialized.
- `AlignmentResult`: orientation, callable-base count, callable identity,
  unresolved-base count, gap-open count, reference segments, and origin-wrap
  status. Score, columns, gapped rows, and operation runs are absent.
- `VariantResult`: one-based position, reference/alternate alleles, kind, and
  mapped calls. Contig and report-only classification/normalization labels are
  absent from the compact result.
- `VariantCallResult`: role, original 0-based call index, optional one-based
  reference position, 0-based PLOC, primary/ambiguity symbols, and optional
  `maximum_peak_height`/`relative_quality`. The two evidence fields are present
  only for supporting calls; flanks do not claim supporting signal evidence.
- `WarningSummaryResult`: exactly the three serialized counts for unresolved
  primary calls, multi-channel unresolved calls, and excluded candidates.
  Operational vendor-disagreement and origin-wrap accounting stays in the
  pipeline rather than the JSON model.

## Invariants and errors

- `schema_version` is `signal.analysis/v5`.
- All intervals are 0-based half-open; variant and mapped reference positions are
  1-based; call indexes and PLOC values are 0-based.
- Inserted supporting calls omit `position`; supporting calls include maximum peak
  height and relative quality; flanking calls omit both evidence fields.
- The document is deterministic: identical completed analysis inputs produce
  identical serialized values.

## Dependencies

- `model::alignment::Orientation`.
- `model::reference::ReferenceTopology`.
- `model::variant::{VariantCallRole, VariantKind}`.
- `serde` for serialization.

## Biological semantics

The v5 contract exposes only the information needed to identify the analysis,
locate the retained read and noisy regions, judge the selected alignment, and
review normalized variants with their direct supporting/flanking calls. It omits
raw or duplicative scientific payloads while preserving the coordinate and signal
quality evidence needed for variant review.

## Tests

No dedicated unit tests; report assembly, projection, schema validation, and
integration tests exercise these types.

## Status

Implemented.
