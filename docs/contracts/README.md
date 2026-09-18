# Production Contracts

Signal keeps public contracts small and versioned. Do not duplicate serialized
shape or implementation details in separate narrative notes.

## Machine-visible contracts

- [`signal.analysis/v5`](../schemas/analysis-v5.schema.json): exact reference-guided JSON shape.
- [`signal.basecalls/v1`](../schemas/basecalls-v1.schema.json): exact reference-free JSON shape.
- [Coordinate conventions](coordinates.md): coordinate domains shared by public results.
- [Synthetic examples](../examples/): illustrative schema-valid outputs.
- [`config/signal.toml`](../../config/signal.toml): checked-in configuration surface.

JSON Schema is authoritative for serialized shape. Rust types and validators are
authoritative for invariants that JSON Schema or TOML syntax cannot express.

## Result semantics

### `signal.basecalls/v1`

`signal basecall <trace.ab1>` runs the shared decode, re-calling,
signal-observation, and quality-control path without loading a reference.

The result contains provenance, complete primary/ambiguity/retained sequences,
trim bounds, merged candidate-noisy regions, and warning counts. It contains no
reference, alignment, or variant interpretation.

Because complete sequence strings can identify a sample, the result follows the
same data-handling policy as its source AB1.

Implementation ownership: [`docs/src/report/basecall.md`](../src/report/basecall.md).

### `signal.analysis/v5`

`signal analyze <trace.ab1> --reference <reference.fasta>` publishes a compact
reference-guided result containing provenance, read/trim summary, merged
candidate-noisy regions, selected alignment summary, normalized variants with
direct mapped-call evidence, and warnings.

The compact contract deliberately omits full read sequences, rolling windows,
gapped alignment rows, method constants, complete per-channel peak objects,
vendor payloads, and compatibility fields.

Variant positions are 1-based on the supplied reference strand. Call indexes and
PLOC sample indexes are 0-based. Interval objects are 0-based half-open. Detailed
coordinate rules live in [coordinates.md](coordinates.md).

Implementation ownership:
[`docs/src/report/json.md`](../src/report/json.md),
[`docs/src/report/variant.md`](../src/report/variant.md), and
[`docs/src/report/signal.md`](../src/report/signal.md).

## Configuration contract

Both commands load one strict configuration from `SIGNAL_CONFIG` or
`config/signal.toml`. Signal does not parse `.env` and does not support
per-setting environment overrides.

The current configuration schema version is `4`. Unknown or duplicate keys,
missing required fields, non-finite values, unsupported versions, and invalid
ranges fail rather than falling back silently.

Exact parsing and validation ownership lives in
[`docs/src/config/load.md`](../src/config/load.md) and
[`docs/src/config/types.md`](../src/config/types.md). The checked-in TOML is the
human-readable current configuration surface.

## Versioning rule

Public schema versions are immutable contracts. Incompatible serialized-output
changes require a new schema version rather than a compatibility wrapper or
silent mutation of an existing version.
