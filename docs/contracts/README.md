# Production Contracts

This directory indexes machine-visible and user-visible contracts. Existing contract files remain at their current paths while the documentation structure is improved incrementally.

## Current contracts

- [Configuration](../configuration.md): strict TOML and environment behavior.
- [Basecall result](../basecall-output.md): `signal.basecalls/v1`.
- [Sample evidence result](../sample-output.md): `signal.sample_evidence/v4`.
- [Analysis result](../json-output.md): `signal.analysis/v6`.
- [Coordinate conventions](coordinates.md): shared coordinate domains and interval semantics.
- [Analysis JSON Schema](../schemas/analysis-v6.schema.json).
- [Basecall JSON Schema](../schemas/basecalls-v1.schema.json).
- [Sample evidence JSON Schema](../schemas/sample-evidence-v4.schema.json).
- [Synthetic examples](../examples/).

A schema is authoritative for the exact serialized shape of its named version. Human contract documentation defines semantics that are not expressible in JSON Schema alone.
