# Signal Roadmap

## Implemented MVP

- strict one-file CLI, TOML configuration, typed errors, and resource caps;
- bounds-checked canonical ABIF decode and one-record FASTA loading;
- signal-derived PLOC re-calling with explicit ambiguity evidence;
- uncalibrated relative quality and end-only trimming;
- bounded forward/reverse semi-global Gotoh with circular topology;
- primary-sequence SNV and ≤50 bp indel extraction/normalization;
- compact `signal.analysis/v3` JSON with concise coordinates, mapped variant calls, and atomic no-overwrite publication;
- synthetic unit/integration tests, source/manual mirror, schemas, and CI gates.

## Release evidence still required

An approved, non-identifying or redistributable real AB1 must exercise the complete rCRS path with documented checksum, expected orientation/region, effective config, normalized differences, runtime, and memory. This is validation evidence, not missing product code.

## Post-MVP candidates

1. approved real-trace regression corpus;
2. empirically calibrated quality/confidence model;
3. mixed-base and two-allele decomposition with validated heteroplasmy limits;
4. additional reference topologies/formats and compressed FASTA;
5. indexed search for longer/multi-contig references;
6. SCF input;
7. batch/parallel orchestration;
8. optional derived interchange formats only under a separate versioned contract.

Each candidate requires SRS/ADR/schema changes, mirrored source docs, focused tests, and biological validation.
