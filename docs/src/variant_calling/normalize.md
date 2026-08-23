# `src/variant_calling/normalize.rs`

## Purpose

Produces minimal, left-normalized (or circular-canonical) indel and SNV
representations, preserving the mapped original-call evidence.

## Responsibilities

- Build SNV, insertion, and deletion `Variant` records with one-based positions.
- Left-normalize linear indels and canonicalize circular indels so equivalent
  repetitive indels share one representation.
- Validate call mappings and carry them through unchanged.

## Non-responsibilities

No extraction, mapping construction, or serialization.

## Key types and functions

- `snv(reference, position, alternate, calls) -> Result<Variant>`.
- `insertion(reference, previous, next, inserted, calls) -> Result<Variant>`.
- `deletion(reference, previous, first_deleted, next, deleted, calls) -> Result<Variant>`.
- `observed_anchor`, `shift_linear`, `canonical_circular`, `build_insertion`,
  `build_deletion`, `validated`, `reference_base`: helpers.

## Invariants and errors

- Indel alleles must be non-empty; otherwise `Error::Variant`.
- Reference positions and anchors are bounds-checked; out-of-range returns
  `Error::Variant`.
- When no aligned left flank exists, the actual reference predecessor is derived
  from the event position; a true linear origin insertion/deletion right-anchors
  to the next reference base.
- Circular repeat normalization walks the whole circle, so the resulting
  representation is anchor-independent.
- Emitted reference alleles are validated against the supplied reference;
  disagreement returns `Error::Variant`.
- Equivalent repetitive indels normalize to the same `(contig, position, ref,
  alt)` tuple.
- Linear references use left normalization and circular references use bounded
  canonical rotation; the algorithm remains explicit even though compact v5 does
  not emit a fixed normalization label.
- Call mappings are validated by `mapping` and preserved through normalization:
  the reported variant's calls are exactly the observed supporting/flanking calls.

## Dependencies

- `model::coordinate` for `reference_one_based`.
- `model::reference` for `Reference` and `ReferenceTopology`.
- `model::variant` for `Variant`, `VariantCallMapping`, `VariantKind`.
- `mapping` for call validation.
- `error` for `Error`/`Result`.

## Biological semantics

Left normalization shifts an indel to the leftmost equivalent position in a
homopolymer or repeat, so the same biological event is always reported at the
same coordinates. Circular references use a canonical rotation instead. The
normalized coordinates may move the reported position, but the original-call
mappings are retained so the observed evidence is never re-assigned.

## Tests

- `left_normalizes_homopolymer_insertion`: verifies a homopolymer insertion
  shifts to the leftmost position.
- `normalization_preserves_observed_call_positions`: verifies that the mapped
  call positions survive normalization unchanged.
- `circular_normalization_is_bounded`: verifies circular canonicalization is
  bounded and correct.
- `circular_repeat_normalization_is_anchor_independent` and
  `circular_insertion_normalization_is_anchor_independent`: verify repeat indels
  normalize identically regardless of observed anchor.
- `derives_internal_linear_predecessor_without_an_aligned_left_flank` and
  `derives_non_origin_circular_predecessor_without_an_aligned_left_flank`: verify
  the actual reference predecessor is derived when the left flank is missing.
- `rejects_reference_alleles_that_disagree_with_the_reference`: verifies the
  emitted-reference integrity guard.

## Status

Implemented.
