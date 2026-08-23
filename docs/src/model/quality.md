# `src/model/quality.rs`

## Purpose

Defines the relative quality scores and auditable end-trim bounds produced by
quality control.

## Responsibilities

- Represent per-call quality evidence and the retained interval.

## Non-responsibilities

No scoring, trimming, or algorithm logic.

## Key types and functions

- `CallQuality`: index, penalty, relative quality score, calibration flag, vendor
  quality, and whether vendor quality applies.
- `QualityControlResult`: per-call records, trim bounds, and the retained
  sequence.

## Invariants and errors

- One quality record per call.
- Trim bounds are within the call range and retain at least the configured
  minimum number of bases.

## Dependencies

No external dependencies; report serialization uses separate compact result types.

## Biological semantics

Quality scores are relative and uncalibrated (`phred_calibrated` is `false`); they
rank calls by local ambiguity and peak-spacing penalties. The retained interval is
the auditable read section kept for alignment.

## Tests

No dedicated unit tests; behavior is exercised through `quality_control`.

## Status

Implemented.
