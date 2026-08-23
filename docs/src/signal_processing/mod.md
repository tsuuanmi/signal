# `src/signal_processing/mod.rs`

## Purpose

Provides the observation-only signal-processing stage.

## Responsibilities

- Accept the immutable decoded chromatogram, signal-derived calls, and strict signal-processing configuration.
- Sequence rolling feature calculation and candidate-noisy region merging.
- Return one typed `SignalAnalysis` without mutating calls or channels.

## Non-responsibilities

No ABIF decoding, channel smoothing, baseline correction, peak selection, quality scoring, alignment, variant filtering, reporting, logging, or file I/O.

## Key function

- `analyze(trace, calls, config) -> Result<SignalAnalysis>`.

## Dependencies

- `features` and `regions` for algorithms.
- `config`, `error`, and `model` for boundary types.

## Status

Implemented.
