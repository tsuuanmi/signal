# `src/report/signal.rs`

## Purpose

Owns the single projection from internal signal analysis to compact merged-region
result records.

## Responsibilities

Consume `SignalAnalysis`, omit rolling windows, and map merged call/sample
intervals plus minimum primary SNR into `SignalQualityResult`.

## Non-responsibilities

No feature calculation, region merging, policy decisions, serialization, or
publication.

## Dependencies

`model::signal` and shared interval/signal result records.

## Tests

Analysis and basecall integration/schema tests exercise both projection callers.
