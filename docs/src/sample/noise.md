# `src/sample/noise.rs`

## Purpose

Projects existing observation-only merged noisy-region context from each immutable
`ReadObservation` into call-backed sample evidence.

## Responsibilities

- Accept one original call index already resolved by differential-locus or normalized-variant aggregation.
- Return whether that call lies inside any existing half-open `NoisyRegion` call interval.
- Reuse the signal-processing region result exactly; do not recompute SNR, merge windows, or introduce another threshold.

## Non-responsibilities

No read rejection, local contribution eligibility, consensus weighting, variant
filtering, artifact classification, confidence scoring, or public JSON projection.

## Invariants

The helper is a pure projection of upstream observation-only state. A `true`
value means only that the call coordinate is covered by a merged candidate-noisy
region under `signal.windowed_snr/v1`. It does not mean the individual call is
known to be weak or erroneous.

## Status

Implemented.
