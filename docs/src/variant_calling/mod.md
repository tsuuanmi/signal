# `src/variant_calling/mod.rs`

## Purpose

Converts the primary-sequence alignment into normalized primary-sequence
variants, preserving the mapping to original trace calls.

## Responsibilities

- Re-export `call` as the module boundary.
- Extract SNVs and ≤50 bp insertions/deletions, exclude unresolved alleles, map
  each variant to its original calls, and left-normalize (or
  circular-canonicalize) indels.

## Non-responsibilities

No heteroplasmy inference, breakpoint detection, two-allele decomposition,
allelic fraction fitting, or serialization.

## Key types and functions

- `call(alignment, reference, config) -> Result<VariantCallingResult>`: the public
  entry point, re-exported from `extract`.
- Child modules: `extract` (alignment-difference extraction), `mapping`
  (original-call/reference mappings), `normalize` (left/circular normalization).

## Invariants and errors

Variants use validated alleles and explicit coordinates. Equivalent repetitive
indels normalize to the same `(contig, position, ref, alt)` tuple. Unresolved or
oversized differences are excluded with a count.

## Dependencies

- `config` for `VariantCallingConfig`.
- `model::alignment`, `model::reference`, `model::variant`.
- `error` for `Error`/`Result`.

## Apollo mapping

Primary alignment-difference subset of
`apollo/include/apollo/variant_calling/variant.h`.

## Requirements and decisions

ADR-0001, ADR-0003, ADR-0012; `SRS-VAR-001` through `SRS-VAR-006`.

## Tests

Unit tests in `normalize` cover left normalization, circular canonicalization,
and preservation of observed call mappings. The integration tests exercise variant
extraction through the pipeline.

## Status

Implemented.
