# `src/model/variant.rs`

## Purpose

Defines normalized primary-sequence differences and the direct mappings to their
original trace calls.

## Responsibilities

- Represent reportable variants, the variant stage output, and each
  variant-associated call's role and original-call identity.
- Carry optional biological reference positions for each mapped call.

## Non-responsibilities

No extraction, normalization, or inference.

## Key types and functions

- `VariantKind`: `Snv`, `Ins`, `Del`.
- `VariantCallRole`: `Supporting` (an observed alternate base) or `Flanking` (a
  reference-aligned call that bounds an indel).
- `VariantCallMapping`: role, the 0-based original call index, and an optional
  reference position that is absent only for inserted query calls.
- `Variant`: contig, one-based position, reference/alternate alleles, kind,
  classification, normalization, and the mapped calls.
- `VariantCallingResult`: reported variants and the count of excluded candidates.

## Invariants and errors

- Variants use validated alleles and explicit one-based coordinates.
- Equivalent repetitive indels normalize to the same `(contig, position, ref,
  alt)` tuple.
- `reference_position_0based` is `None` only for inserted query calls; deletion
  evidence is flanking calls only.

## Dependencies

- `serde` for serialization of `VariantKind` and `VariantCallRole`.

## Biological semantics

Variants are primary-sequence differences between the read and the reference:
single-nucleotide substitutions and small insertions/deletions. `classification`
is always `primary_sequence_difference`; `normalization` records whether the
variant was left-normalized (`linear_left`) or circular-canonicalized
(`circular_canonical`). Each reported difference keeps a direct mapping back to
the original trace calls that support or flank it, so the normalized coordinates
do not lose the observed call evidence.

## Tests

No dedicated unit tests; behavior is exercised through `variant_calling`.

## Status

Implemented.
