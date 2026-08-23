# Signal JSON-Only MVP Delivery Record

## Objective

Deliver one auditable AB1-to-primary-difference vertical slice in Rust. The implementation accepts one canonical analyzed ABIF/AB1, one strict config, and one single-record FASTA; then decodes, re-calls, trims, aligns, normalizes variants, and atomically publishes one JSON result.

## Completed implementation phases

1. Repository governance, one-to-one source manuals, strict config, schema, and reference identity.
2. Validated config/domain models, checked ABIF directory parsing, canonical tag decode, and FASTA loading.
3. PLOC-window signal re-calling, ambiguity evidence, relative quality, and end trimming.
4. Bounded affine-gap semi-global alignment, deterministic traceback, strand selection, and circular reference projection.
5. Primary SNV/small-indel extraction, linear/circular normalization, typed JSON assembly, and atomic no-overwrite output.
6. Synthetic malformed/unit/end-to-end tests, deterministic output checks, and CI contract gates.

## Command and output

```text
signal analyze <trace.ab1> --reference <reference.fasta>
```

Success creates only `results/<trace-stem>.json`. Failure creates no result. Existing targets are never overwritten.

## Acceptance

- canonical ABIF records are bounds-checked and inconsistent arrays are rejected;
- JSON exposes versioned method/configuration identity and variant-associated evidence; effective parameters remain in the strict TOML;
- internal coordinates and external 1-based variants are explicit;
- circular rCRS origin-spanning reads are representable;
- no genotype, heteroplasmy fraction, clinical meaning, VCF/BCF, or hidden regional correction is emitted;
- format/check/Clippy/tests/rustdoc/schema/TOML/reference/docs-mirror gates pass;
- approved real-trace validation is recorded before a scientific release claim.

See `pipeline.md` for formulas and `compatibility.md` for intentional Apollo divergences.
