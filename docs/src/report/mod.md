# `src/report/mod.rs`

## Purpose

Provides compact v5 JSON assembly/serialization and atomic no-overwrite
publication.

## Responsibilities

- Re-export `CompletedAnalysis`, `build`, `serialize`, and `publish` to pipeline
  orchestration.
- Keep typed v5 assembly, concise variant evidence projection, and atomic
  publication in separate child modules.

## Non-responsibilities

No basecalling, signal feature calculation, quality scoring, alignment, variant
inference/filtering, or operational logging.

## Key types and functions

- `build(completed) -> Result<AnalysisResult>`: assembles `signal.analysis/v5`.
- `serialize(result) -> Result<Vec<u8>>`: produces deterministic JSON bytes.
- `publish(path, bytes) -> Result<()>`: atomically publishes a new result without
  overwriting an existing target.
- Child modules: `json` (v5 assembly/serialization), `variant` (essential mapped
  supporting evidence), and `atomic` (publication transaction).

## Invariants and errors

JSON identifies `signal.analysis/v5`; serialization is deterministic; publication
is atomic and no-overwrite. Assembly, serialization, and filesystem failures
propagate as typed errors.

## Dependencies

- Completed model and stage outputs used by `json` and `variant`.
- `error` for typed failures.

## Tests

Integration tests exercise deterministic v5 serialization and no-overwrite
publication; atomic publication also has focused unit coverage.

## Status

Implemented.
