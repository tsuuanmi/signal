# `src/pipeline/mod.rs`

## Purpose

Defines orchestration boundaries for production commands and explicit local validation export.

## Responsibilities

- Expose `analyze`, `basecall`, and `sample` as production command boundaries.
- Expose the crate-private validation-export entry used by the public `validation` module.
- Share validated input helpers, reference-independent read stages, reference-guided observation processing, multi-trace sample-read processing, and terminal operation/logging failure preservation.

## Non-responsibilities

No binary parsing, scoring loops, variant normalization, threshold fitting, or serialization-format logic.

## Key types and functions

- `analyze(args)`, `basecall(args)`, and `sample(args)`: production command entry points.
- `validation_export(request)`: local measurement-export orchestration entry.
- Child modules separate input loading, read/observation science, sample-read reuse, sample metrics, command orchestration, and validation export.
- `record_failure`: shared terminal error-log and synchronization policy.

## Invariants and errors

- Production commands return success only after their result output is committed.
- Validation export returns success only after its ignored local measurement file is committed.
- Stage errors propagate as typed `Error` values.
- The ignored local data corpus is never auto-discovered.

## Dependencies

- `cli` for production command arguments.
- `validation` for the explicit validation request type.
- `error`, `logger`, and `Instant` for the shared failure boundary.

## Requirements and decisions

ADR-0001, ADR-0002, ADR-0007, ADR-0044; `SRS-VAL-005`.

## Tests

Production integration tests cover analyze/basecall/sample; `tests/validation.rs` covers the local validation export.

## Status

Implemented.
