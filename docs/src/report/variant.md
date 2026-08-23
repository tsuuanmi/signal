# `src/report/variant.rs`

## Purpose

Projects normalized variants and their mapped original calls into the compact
`signal` variant records, joining them to chromatogram peaks and call quality.

## Responsibilities

- Turn each `Variant` into a `VariantResult` and each `VariantCallMapping` into a
  `VariantCallResult`.
- Look up the original call and its quality record by index and emit the PLOC,
  primary/ambiguity symbols, channel peaks, and non-redundant quality fields.
- Convert internal 0-based positions to the one-based report reference position,
  leaving it absent for inserted calls.

## Non-responsibilities

No document assembly, serialization, atomic publication, or algorithm logic.

## Key types and functions

- `project(variants, calls, quality) -> Result<Vec<VariantResult>>`: the module
  entry point, called by `report::json::build`.
- `project_variant`, `project_call`, `channel_peaks`, `peak_result`,
  `quality_result`: helpers.

## Invariants and errors

- A mapping referencing a missing call or quality index returns `Error::Report`.
- The mapping index must match the referenced call and quality records; otherwise
  `Error::Report`.
- `position` is `None` for inserted calls and the checked one-based reference
  position otherwise.

## Dependencies

- `model::basecalls` for `BaseCall`, `BaseCalls`, `ChannelPeak`.
- `model::coordinate` for `reference_one_based`.
- `model::quality` for `CallQuality`, `QualityControlResult`.
- `model::result` for the projection result types.
- `model::variant` for `Variant`, `VariantCallMapping`.
- `error` for `Error`/`Result`.

## Biological semantics

This module is the single place that turns a normalized variant plus its original
trace calls into report records. The reported reference `position` is 1-based;
the trace `ploc` and channel peak positions are the 0-based chromatogram sample
coordinates at which the call was observed. Variant alleles use the reference
strand, while projected call bases and A/C/G/T peaks retain the original trace
strand.

## Tests

No dedicated unit tests; behavior is exercised through `report::json` and the
integration tests.

## Status

Implemented.
