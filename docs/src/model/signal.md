# `src/model/signal.rs`

## Purpose

Defines the internal observation-only signal-quality result.

## Responsibilities

- Represent one rolling call/sample window with minimum primary SNR, maximum
  secondary SNR, and the candidate-noisy decision. Maximum secondary SNR remains
  internal for the pipeline's operational aggregate and is omitted from compact
  v5.
- Mark candidate-noisy windows without changing any scientific call.
- Represent the deterministic union of overlapping or adjacent candidate-noisy windows.
- Provide aggregate noisy-window and noisy-call counts for operational logging.

## Non-responsibilities

No feature calculation, threshold validation, smoothing, base calling, trimming, variant filtering, serialization, or file I/O.

## Key types

- `SignalWindow`: 0-based half-open call/sample intervals, minimum primary SNR,
  internal maximum secondary SNR, and candidate-noisy flag.
- `NoisyRegion`: merged call/sample intervals and minimum primary SNR.
- `SignalAnalysis`: ordered windows and merged regions, with aggregate count helpers. Isolated candidate windows can remain in `windows` without appearing in `noisy_regions`.

## Invariants

All intervals are ordered in original trace orientation. SNR values are finite and non-negative. Regions do not overlap and do not bridge clean gaps.

## Dependencies

None outside the standard library.

## Status

Implemented.
