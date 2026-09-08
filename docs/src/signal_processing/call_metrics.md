# `src/signal_processing/call_metrics.rs`

## Purpose

Derives one internal local-context signal record per original base call from existing rolling-window geometry and optional primary-event evidence.

## Responsibilities

- Select a deterministic nearby full-width rolling context for each call using the configured signal window size.
- Reuse the selected rolling context's validated call and sample intervals.
- Estimate independent local baseline and noise sigma for A/C/G/T with shared statistics primitives.
- Transform optional co-located primary-event raw values into corrected amplitudes and six-decimal SNR values.
- Preserve calls with no unique primary event by retaining their local channel context with no primary-event metrics.

## Non-responsibilities

No peak selection, call classification, candidate-noisy decision, region merging, quality scoring, trimming, alignment, variant filtering, reporting, or serialization.

## Invariants and errors

- Output has one `CallSignalMetrics` record per `BaseCall` in original call order.
- Each context is an existing rolling window of exactly `window_size_bases` calls and contains its target call.
- Context selection centers when possible, uses the first window at the left edge, and the last window at the right edge. Even widths retain one extra call on the right.
- A/C/G/T arrays follow `Nucleotide::ALL` order.
- Derived primary-event values use co-located raw evidence, never a channel's remote selected peak.
- An impossible rolling-window count or invalid selected context returns `Error::SignalProcessing`.

## Tests

Tests cover odd/even context placement, metric count and ordering, baseline-zero/floor-noise amplitudes and SNR, remote-secondary separation, and calls with no primary event.

## Status

Implemented.
