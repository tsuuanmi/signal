# `src/report/mod.rs`

## Purpose

Serializes the completed analysis result into a versioned JSON document and
publishes it atomically.

## Responsibilities

- Re-export `build`, `serialize`, `CompletedAnalysis`, and `publish`.
- Assemble the compact `signal.analysis/v4` document and write it atomically.
- Keep the variant-call projection in a separate `variant` submodule.

## Non-responsibilities

No basecalling, quality scoring, alignment, variant inference, or hidden
filtering.

## Key types and functions

- `build(completed) -> Result<AnalysisResult>`: assembles the compact v4 document,
  delegating variant-call projection to `variant`.
- `serialize(result) -> Result<Vec<u8>>`: deterministic JSON bytes.
- `publish(path, bytes) -> Result<()>`: atomic no-overwrite publication.
- Child modules: `json` (assembly and serialization), `variant` (projection of
  variant-associated calls), `atomic` (publication).

## Invariants and errors

JSON identifies `signal.analysis/v4`; serialization is deterministic; the output
is written atomically and never overwrites an existing target. Assembly,
serialization, and output failures return typed errors.

## Dependencies

- `model::result` and the other model types.
- `error` for `Error`/`Result`.

## Apollo mapping

Replaces the output responsibilities of `apollo/include/apollo/report/json.h`
with a versioned contract.

## Requirements and decisions

ADR-0011, ADR-0012, ADR-0013; `SRS-OUT-001` through `SRS-OUT-007`.

## Tests

The integration tests exercise deterministic serialization and no-overwrite
publication.

## Status

Implemented.
