# `src/model/signal.rs`

## Purpose

Defines the internal observation-only signal-quality result.

## Responsibilities

- Represent one rolling call/sample window with minimum primary SNR, maximum
  secondary SNR, and the candidate-noisy decision. Maximum secondary SNR remains
  internal for the pipeline's operational aggregate and is omitted from compact
  v5.
- Represent per-call local A/C/G/T baseline/noise context and optional derived
  primary-event corrected amplitudes and SNR observations.
- Mark candidate-noisy windows without changing any scientific call.
- Represent the deterministic union of overlapping or adjacent candidate-noisy windows.
- Provide aggregate noisy-window and noisy-call counts for operational logging.

## Non-responsibilities

No feature calculation, threshold validation, smoothing, base calling, trimming, variant filtering, serialization, or file I/O.

## Key types

- `SignalWindow`: 0-based half-open call/sample intervals, minimum primary SNR,
  internal maximum secondary SNR, and candidate-noisy flag.
- `PrimaryEventSignalMetrics`: the existing primary-event sample coordinate plus
  baseline-corrected A/C/G/T amplitudes and local SNR values; raw channel values
  remain owned by `BaseCall` evidence.
- `CallSignalMetrics`: one call index, its selected rolling context, independent
  A/C/G/T baselines/noise sigmas, and optional primary-event metrics.
- `NoisyRegion`: merged call/sample intervals and minimum primary SNR.
- `SignalAnalysis`: ordered per-call metrics, windows, and merged regions, with
  aggregate count helpers. Isolated candidate windows can remain in `windows`
  without appearing in `noisy_regions`.

## Invariants

All intervals are ordered in original trace orientation. A/C/G/T arrays follow
`Nucleotide::ALL`; SNR values are finite and non-negative; corrected amplitudes
are non-negative. Regions do not overlap and do not bridge clean gaps.

## Dependencies

None outside the standard library.

## Status

Implemented.
