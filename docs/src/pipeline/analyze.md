# `src/pipeline/analyze.rs`

## Purpose

Sequences the complete end-to-end scientific stages for one AB1-to-JSON
analysis.

## Responsibilities

- Load inputs, then run basecalling, quality control, alignment, and variant
  calling in order.
- Assemble the compact `signal.analysis/v3` document, serialize it, and publish it
  atomically to `results/<trace-stem>.json` without overwriting an existing target.

## Non-responsibilities

No binary parsing, scoring loops, variant normalization, or serialization format
logic.

## Key types and functions

- `run(args) -> Result<()>`: the entry point, re-exported from `mod.rs`.

## Invariants and errors

- The pipeline returns success only after the JSON output is committed.
- Stage errors propagate as typed `Error` values; no stage is skipped silently.
- The output is written atomically and never overwrites an existing target.

## Dependencies

- `input`, `basecalling`, `quality_control`, `alignment`, `variant_calling`,
  `report`.
- `cli` for `AnalyzeArgs`.
- `error` for `Result`.

## Biological semantics

The stage order reflects the analysis flow: decode the chromatogram, re-call
bases, score quality and trim ends, align the retained read, and extract
primary-sequence differences.

## Tests

No dedicated unit tests; the end-to-end `tests/analyze.rs` integration tests
exercise the complete pipeline.

## Status

Implemented.
