# Production Contracts

This directory indexes machine-visible and user-visible contracts. Existing contract files remain at their current paths while the documentation structure is improved incrementally.

## Current contracts

- [Configuration](../configuration.md): strict TOML and environment behavior.
- [Basecall result](../basecall-output.md): `signal.basecalls/v1`.
- [Analysis result](../json-output.md): `signal.analysis/v5`.
- [Coordinate conventions](coordinates.md): shared coordinate domains and interval semantics.
- [Analysis JSON Schema](../schemas/analysis-v5.schema.json).
- [Basecall JSON Schema](../schemas/basecalls-v1.schema.json).
- [Synthetic examples](../examples/).

A schema is authoritative for the exact serialized shape of its named version. Human contract documentation defines semantics that are not expressible in JSON Schema alone.
