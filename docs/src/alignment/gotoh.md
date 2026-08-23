# `src/alignment/gotoh.rs`

## Purpose

Runs bounded, semi-global affine-gap Gotoh dynamic programming over a query and
reference, returning up to two distinct equally scoring placements.

## Responsibilities

- Build the match/insertion/deletion dynamic-programming matrices with affine gap
  costs (open + k × extension).
- Enforce the compiled `MAX_ALIGNMENT_CELLS` cap before allocating traceback
  storage.
- Rank final-row endpoints and recover up to two distinct, equally scoring
  placements so downstream strand selection can reject ambiguous results.
- Support circular references by selecting the best endpoint whose traceback
  consumes at most `modulo_length`, then deduplicate by wrapped start.

## Non-responsibilities

No strand selection, quality filtering, variant extraction, or output
formatting. It does not decide between forward and reverse orientation.

## Key types and functions

- `align(query, reference, config, modulo_length) -> Result<Vec<RawAlignment>>`:
  the DP entry point. Returns one or two placements, or a typed error.
- `state_priority(state) -> u8`: deterministic tie-break order (Match > Deletion
  > Insertion) used when diagonal predecessors score equally.

## Invariants and errors

- Query and reference must both be non-empty; otherwise `Error::Alignment`.
- Cell count is checked with `checked_mul` and rejected when it exceeds
  `MAX_ALIGNMENT_CELLS`.
- All matrix indices are bounds-checked; overflow yields `Error::Alignment`.
- If no valid bounded traceback is found, `Error::Alignment` is returned.
- Placements are deduplicated by wrapped start and gapped rows; the function
  stops early once two distinct placements are found.

## Dependencies

- `scoring` for `NEGATIVE_INFINITY`, `State`, `add`, and `substitution`.
- `traceback` for `RawAlignment`, `TracebackInput`, and `decode`.
- `config` for `AlignmentConfig` and `MAX_ALIGNMENT_CELLS`.
- `error` for `Error`/`Result`.

## Biological semantics

Affine-gap scoring models the cost of sequencing insertions and deletions as a
single open penalty plus a per-base extension penalty. Semi-global alignment
allows the reference flanks to remain unaligned, which is appropriate when the
query is a read that should be placed within a longer reference.

## Tests

- `permits_free_reference_flanks`: verifies a query placed inside a longer
  reference scores only the matched bases.
- `accepts_one_full_circular_reference_span`: verifies a one-circle traceback is
  retained under the circular bound.
- `scores_one_base_gap_as_open_plus_extension`: verifies a single-base insertion
  costs open + extension and produces the expected operation run.
- `preserves_scores_beyond_i32_range`: verifies the DP retains an exact 64-bit score.

## Status

Implemented.
