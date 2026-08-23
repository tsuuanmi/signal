# Signal JSON-Only MVP Delivery Record

## Objective

Deliver one auditable AB1-to-primary-difference vertical slice in Rust. The implementation accepts one canonical analyzed ABIF/AB1, one strict config, and one single-record FASTA; then decodes, re-calls, trims, aligns, normalizes variants, and atomically publishes one JSON result.

## Completed implementation phases

1. Repository governance, one-to-one source manuals, strict configuration, versioned output schema, and reference identity.
2. Validated config/domain models, checked ABIF directory parsing, canonical tag decode, and FASTA loading.
3. PLOC-window signal re-calling, ambiguity evidence, relative quality, and end trimming.
4. Bounded affine-gap semi-global alignment, deterministic traceback, strand selection, and circular reference projection.
5. Primary SNV/small-indel extraction, linear/circular normalization, typed JSON assembly, and atomic no-overwrite output.
6. Observation-only rolling signal analysis and merged candidate-noisy regions.
7. Compact `signal.analysis/v5` projection retaining provenance, read/trim,
   merged noisy-region, alignment, normalized-variant, and warning summaries
   without raw or redundant payloads.
8. Clean external batch reruns with complete preflight/build before selected-only
   destructive cleanup.
9. Synthetic malformed/unit/end-to-end tests, deterministic output checks, and
   CI contract gates.

## Command and output

```text
signal analyze <trace.ab1> --reference <reference.fasta>
```

A successful core CLI invocation creates `results/<trace-stem>.json` and appends a separate operational log. Core analysis failure creates no JSON result, and an existing JSON target is never overwritten. The external batch wrapper has separate selected-cleanup semantics documented in `data.md`; a later batch failure may leave partial new outputs.

## Acceptance

- canonical ABIF records are bounds-checked and inconsistent arrays are rejected;
- compact v5 JSON exposes software and input/reference/configuration hashes, call count/trim, merged noisy regions, alignment summary, normalized variants with concise mapped supporting evidence, and warning counts; effective parameters remain in strict configuration schema v4;
- internal coordinates and external 1-based variants are explicit;
- circular rCRS origin-spanning reads are representable;
- filenames, full sequences/windows/gapped rows, method constants, full peaks, vendor data, compatibility output, genotype, heteroplasmy fraction, clinical meaning, VCF/BCF, and hidden regional correction are not emitted;
- format/check/Clippy/tests/rustdoc/schema/TOML/reference/docs-mirror gates pass;
- batch cleanup is limited to fully preflighted selected sample directories and matching logs, rejects ambiguity/collisions/symlinks, and preserves unselected artifacts;
- approved real-trace validation is recorded before a scientific release claim.

See `pipeline.md` for formulas and `compatibility.md` for intentional Apollo divergences.
