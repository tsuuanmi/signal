# `src/pipeline/mod.rs`

## Purpose

Defines orchestration boundaries for single-read `analyze`/`basecall` and multi-read `sample` operations.

## Responsibilities

- Expose `analyze`, `basecall`, and `sample` as command boundaries.
- Share validated input helpers, reference-independent read-stage orchestration,
  and terminal operation/logging failure preservation.

## Non-responsibilities

No binary parsing, scoring loops, variant normalization, or serialization format
logic.

## Key types and functions

- `analyze(args)`, `basecall(args)`, and `sample(args)`: command entry points.
- Child modules: `input` (command-specific loading), `read` (reference-independent stages), `observation` (shared read-level reference-guided science), and command-specific `analyze`/`basecall`/`sample` sequencing.
- `record_failure`: shared terminal error-log and synchronization policy.

## Invariants and errors

- The pipeline returns success only after the JSON output is committed.
- Stage errors propagate as typed `Error` values.
- The ignored `data/` corpus is never auto-discovered.

## Dependencies

- `cli` for `AnalyzeArgs` and `BasecallArgs`.
- `error`, `logger`, and `Instant` for the shared failure boundary.

## Apollo mapping

Replaces monolithic command handlers such as `variantcall.h` with explicit stage
boundaries.

## Requirements and decisions

ADR-0001, ADR-0002, ADR-0007; `SRS-IN-001`, `SRS-CFG-001` through
`SRS-CFG-005`, `SRS-OUT-001`, and `SRS-OUT-005`.

## Tests

The end-to-end `tests/analyze.rs` and `tests/basecall.rs` integration tests
exercise both command pipelines.

## Status

Implemented.
