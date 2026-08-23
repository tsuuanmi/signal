# `src/model/alignment.rs`

## Purpose

Defines the pairwise alignment records with explicit strand and coordinates.

## Responsibilities

- Represent the selected alignment only: orientation, score, gapped rows,
  operation runs, reference segments, metrics, and per-column records.
- Losing orientation candidates are not retained.

## Non-responsibilities

No scoring, traceback, or strand selection.

## Key types and functions

- `Orientation`: `Forward` or `Reverse`; serialized as `snake_case`.
- `ReferenceSegment`: a half-open segment on the original reference.
- `AlignmentMetrics`: exact matches, mismatches, gap opens, callable columns,
  callable identity, and unresolved query bases.
- `AlignmentColumn`: one aligned column with query/reference bases and optional
  original indices.
- `Alignment`: the selected alignment only — orientation, `i64` score, gapped
  rows, operation runs, reference segments, origin-wrap flag, metrics, and
  columns.

## Invariants and errors

- Gapped query and reference rows have equal lengths.
- Reference segments are half-open and within the reference.
- Only one orientation is retained after selection; the rejected orientation is
  discarded and absent from the output.

## Dependencies

- `serde` for serialization.

## Biological semantics

The alignment records how the retained read maps onto the reference, including
which strand it matches and whether a circular alignment wraps the origin. This
is the basis for variant extraction.

## Tests

No dedicated unit tests; behavior is exercised through `alignment` and the
integration tests.

## Status

Implemented.
