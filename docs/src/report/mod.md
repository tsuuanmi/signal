# `src/report/mod.rs`

## Purpose

Provides typed analysis-v5/basecalls-v1 assembly, shared serialization, and
atomic no-overwrite publication.

## Responsibilities

- Re-export `CompletedAnalysis`, `CompletedBasecall`, explicit builders, generic
  `serialize`, and `publish` to pipeline orchestration.
- Keep typed contract assembly, shared merged-signal projection, concise variant
  evidence projection, and atomic publication in separate child modules.

## Non-responsibilities

No basecalling, signal feature calculation, quality scoring, alignment, variant
inference/filtering, or operational logging.

## Key types and functions

- `build_analysis(completed)` and `build_basecall(completed)`: assemble typed
  command-specific result contracts.
- `serialize(result) -> Result<Vec<u8>>`: produces deterministic JSON bytes.
- `publish(path, bytes) -> Result<()>`: atomically publishes a new result without
  overwriting an existing target.
- Child modules: `json` (analysis assembly/shared serialization), `basecall`
  (reference-free assembly), `signal` (merged regions), `variant` (mapped
  supporting evidence), and `atomic` (publication transaction).

## Invariants and errors

JSON identifies its analysis-v5 or basecalls-v1 contract; serialization is
deterministic; publication is atomic and no-overwrite. Assembly, serialization, and filesystem failures
propagate as typed errors.

## Dependencies

- Completed model and stage outputs used by `json` and `variant`.
- `error` for typed failures.

## Tests

Integration tests exercise deterministic analysis/basecall serialization and
no-overwrite publication; atomic publication also has focused unit coverage.

## Status

Implemented.
