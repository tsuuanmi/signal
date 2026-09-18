# `src/model/alignment.rs`

## Purpose

Defines the pairwise alignment records with explicit strand and coordinates.

## Responsibilities

- Represent the selected internal alignment only: orientation, score, reference
  segments, origin-wrap status, metrics, and per-column records used by variant
  extraction.
- Losing orientation candidates are not retained.

## Non-responsibilities

No scoring, traceback, strand selection, or sample-level reconciliation.

## Key types and functions

- `Orientation`: `Forward` or `Reverse`; serialized as `snake_case`.
- `ReferenceSegment`: one 0-based half-open segment on the original reference.
- `AlignmentMetrics`: exact matches, mismatches, gap opens, callable columns,
  callable identity, and unresolved query bases.
- `AlignmentColumn`: one aligned column with query/reference bases and optional
  original call/reference indices.
- `Alignment`: the selected orientation, `i64` score, reference segments,
  origin-wrap flag, metrics, and columns. Gapped rows and operation runs are not
  retained in this final model.

## Invariants and errors

- Alignment columns retain enough query/reference and coordinate information for
  variant extraction without retaining duplicate gapped strings.
- Reference segments are half-open and within the reference.
- Only one orientation is retained after selection; the rejected orientation is
  discarded and absent from the output.

## Dependencies

- `serde` for `Orientation` and `AlignmentMetrics` serialization.

## Biological semantics

The alignment records how the retained read maps onto the reference, including
which strand it matches and whether a circular alignment wraps the origin. This
mapping is authoritative for downstream variant extraction and read placement.

## Tests

Alignment behavior is covered by the alignment implementation tests and
end-to-end analysis tests.

## Status

Implemented.
