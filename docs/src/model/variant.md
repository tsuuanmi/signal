# `src/model/variant.rs`

## Purpose

Defines normalized primary-sequence differences and the direct mappings to their
original trace calls.

## Responsibilities

- Represent reportable variants, the variant stage output, and each
  variant-associated call's role and original-call identity.
- Carry optional biological reference positions for each mapped call.
- Represent every excluded candidate with a stable reason list and a concise,
  allele-free identity for pipeline logging.

## Non-responsibilities

No extraction, normalization, or inference.

## Key types and functions

- `VariantKind`: `Snv`, `Ins`, `Del`.
- `VariantCallRole`: `Supporting` (an observed alternate base) or `Flanking` (a
  reference-aligned call that bounds an indel).
- `VariantCallMapping`: role, the 0-based original call index, and an optional
  reference position that is absent only for inserted query calls.
- `Variant`: contig, normalized one-based position, reference/alternate alleles,
  kind, and mapped calls. Report-only classification and normalization labels are
  not stored.
- `VariantExclusionReason`: stable structural, region, peak, and relative-quality
  rejection reasons with operational labels.
- `ExcludedVariant`: contig, optional normalized one-based position, kind, and all
  rejection reasons; alleles are intentionally absent.
- `VariantCallingResult`: configured-eligible variants plus one diagnostic per
  excluded candidate; `excluded_count()` derives the warning count.

## Invariants and errors

- Variants use validated alleles and explicit one-based coordinates.
- Equivalent repetitive indels normalize to the same `(contig, position, ref,
  alt)` tuple.
- `reference_position_0based` is `None` only for inserted query calls; deletion
  evidence is flanking calls only.
- Each excluded candidate appears exactly once. Its reason list is deduplicated by
  rule, and its position is absent when normalization never produced one.

## Dependencies

- `serde` for serialization of `VariantKind` and `VariantCallRole`.

## Biological semantics

Variants are primary-sequence differences between the read and the reference:
single-nucleotide substitutions and small insertions/deletions. Linear-left or
circular-canonical normalization remains algorithmic behavior, but fixed
classification and normalization labels are not retained on `Variant` or emitted
in compact v5. Each reported difference keeps a direct mapping back to the
original trace calls that support or flank it, so normalized coordinates do not
lose observed call evidence.

## Tests

No dedicated unit tests; behavior is exercised through `variant_calling`.

## Status

Implemented.
