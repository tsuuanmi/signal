# `src/pipeline/mod.rs`

## Purpose

Orchestrates the complete `analyze` use case: one AB1, one FASTA, one JSON result,
and one append-only operational log.

## Responsibilities

- Re-export `analyze` as the module boundary.
- Sequence validated input, basecalling, QC, alignment, variant calling, and
  atomic reporting while recording stage summaries through `logger`.

## Non-responsibilities

No binary parsing, scoring loops, variant normalization, or serialization format
logic.

## Key types and functions

- `analyze(args) -> Result<()>`: the public entry point, re-exported from
  `mod.rs`.
- Child modules: `input` (path validation and loading), `analyze` (stage
  sequencing).

## Invariants and errors

- The pipeline returns success only after the JSON output is committed.
- Stage errors propagate as typed `Error` values.
- The ignored `data/` corpus is never auto-discovered.

## Dependencies

- `cli` for `AnalyzeArgs`.
- `error` for `Result`.

## Apollo mapping

Replaces monolithic command handlers such as `variantcall.h` with explicit stage
boundaries.

## Requirements and decisions

ADR-0001, ADR-0002, ADR-0007; `SRS-IN-001`, `SRS-CFG-001` through
`SRS-CFG-005`, `SRS-OUT-001`, and `SRS-OUT-005`.

## Tests

The end-to-end `tests/analyze.rs` integration tests exercise the complete
pipeline.

## Status

Implemented.
