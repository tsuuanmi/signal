# `src/alignment/orient.rs`

## Purpose

Aligns the retained query in both forward and reverse-complement orientations,
selects one unique winner, and projects coordinates onto the reference.

## Responsibilities

- Build forward and reverse-complement queries with their original-call index
  mappings.
- Run Gotoh against the reference, duplicating the sequence for circular
  topologies and bounding the span by the reference length.
- Select the winning orientation by score, then exact matches, then fewer
  mismatches and gap opens; reject ties.
- Enforce the minimum callable bases and minimum callable identity thresholds.
- Produce reference segments, origin-wrap status, and per-column coordinates for
  the selected alignment only; losing orientation candidates are discarded.

## Non-responsibilities

No variant extraction, quality scoring, or output formatting.

## Key types and functions

- `align_best(qc, reference, config) -> Result<Alignment>`: the entry point,
  returning one unique selected `Alignment`.
- `compare(left, right) -> Ordering`: deterministic orientation tie-break.
- `segments(alignment, reference) -> (Vec<ReferenceSegment>, bool)`: projects the
  reference span, splitting it when a circular alignment wraps the origin.

## Invariants and errors

- Forward and reverse orientations that remain equally supported return
  `Error::Alignment`.
- A selected orientation with multiple equally scoring placements is rejected.
- Alignments below `minimum_callable_bases` or `minimum_identity` return
  `Error::Alignment`.
- For circular references, reference indices are reduced modulo the reference
  length and the origin-wrap flag is set when the span crosses the end.

## Dependencies

- `gotoh`, `traceback`, `scoring`.
- `config` for `AlignmentConfig`.
- `model::alignment`, `model::nucleotide` (`reverse_complement`),
  `model::quality`, and `model::reference`.
- `error` for `Error`/`Result`.

## Biological semantics

Sanger reads may be sequenced on either strand. Aligning both orientations and
selecting the better-supported one recovers the true strand relative to the
reference. For circular references (e.g. mitochondrial rCRS), the alignment may
legitimately wrap the origin, which is reported rather than treated as an error.

## Tests

No dedicated unit tests; behavior is exercised through the end-to-end
`tests/analyze.rs` integration tests.

## Status

Implemented.
