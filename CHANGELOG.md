# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Breaking Changes

- Replace `signal.analysis/v1` with compact `signal.analysis/v3`: omit bulk records; use concise coordinate names and direct mapped variant `calls` with A/C/G/T peaks plus relative/vendor quality.
- Remove `--out-prefix`; analyses now publish as `results/<trace-stem>.json` and create the results directory when needed.
- Replace strict configuration schema version 1 with version 2, requiring variant peak, relative-quality, and inclusive-region settings.

### Added

- Complete one-AB1 Rust analysis pipeline with strict TOML configuration and typed errors.
- Bounds-checked canonical ABIF decode, single-record FASTA identity, and internal four-channel signal evidence.
- Signal-derived re-calling at PLOC loci, relative quality scoring, and end-only trimming.
- Bounded deterministic forward/reverse semi-global Gotoh with circular-reference support.
- Normalized primary-sequence SNV and small-indel extraction with original-call evidence.
- Versioned compact `signal.analysis/v3` schema, synthetic example, exact SNV/indel call-to-PLOC mapping tests, atomic no-overwrite publication, and end-to-end tests.
- Exact one-to-one Rust source manuals, normative pipeline documentation, biological limitations, and Apollo deviation records.
- Shared SHA-256 identity helper in `src/checksum.rs`, used by config, trace, and reference loading.
- Locked uv environment and typed schema validator for reproducible JSON contract checks in development and CI.
- External `scripts/analyze_samples.py` wrapper for safe per-sample local-corpus orchestration without changing the one-file CLI.
- Rust-native append-only per-trace operational logging under `logs/`, with `SIGNAL_LOG_DIR` for isolated orchestration and run-correlated, single-line records.

### Changed

- MVP output is one compact `results/<trace-stem>.json`; the earlier JSON-plus-VCF plan is superseded.
- Quality is explicitly uncalibrated relative score; vendor PCON remains separate.
- rCRS topology is circular and origin-spanning alignments/indels have explicit canonical coordinates.
- Basecalling is `signal.peak_recall/v2`: one/two/three qualifying channels behave canonical / strongest+IUPAC / strongest+unresolved-ambiguity, and four produce unresolved primary+ambiguity N.
- Variant calling is `signal.primary_difference/v3`: normalized anchors must lie in configured inclusive regions; SNV and every inserted-base supporting call must meet the configured maximum-channel peak floor and strictly exceed the relative-quality threshold; deletion and insertion flanks are exempt.
- Alignment scores are 64-bit (`i64`) while configuration score deltas remain 32-bit (`i32`).
- An origin-crossing circular alignment sets a boolean `reference_origin_wrap` in the warning summary instead of an info warning string.
- `P2BA.1` is ignored; only optional `PBAS.2` and `PCON.2` vendor evidence is consumed.
- Relative quality scores manually clamp the score fraction to `[0, 1]` so results stay in `[0, max_relative_quality_score]`.
- Operational logs now record concise aggregate metrics and timings for every processing stage, exact warning categories, stage-aware failures, and each removed variant's kind/position/reasons without alleles or raw scientific payloads.
- The bundled `variant_calling.minimum_peak_height` is raised from 100 to 150.

### Fixed

- Accept uppercase IUPAC vendor base evidence and both one-byte ABIF PCON element representations without changing signal-derived calls.
- Avoid stale PID-only temporary-output name collisions and remove a just-published target when final synchronization fails.
- Select the best span-valid circular traceback when a higher-scoring unbounded candidate exists in the doubled reference.
- Canonicalize origin-spanning repeat indels independently of their observed anchor while preserving observed call mappings.
- Derive indel anchors from the actual adjacent reference coordinate at alignment boundaries and reject any emitted reference allele that disagrees with the supplied reference.
- Prevent four-channel unresolved loci from contributing a guessed primary base and use 64-bit alignment scores without saturation.

### Removed

- Not-implemented scaffold behavior and all planned VCF/BCF compatibility paths.
- Misleading fully de novo terminology, hardcoded poly-C/HV behavior, and genotype/heteroplasmy claims from MVP scope.
- `src/reference/checksum.rs`; SHA-256 is consolidated into the shared `src/checksum.rs`.
