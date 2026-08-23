# `src/alignment/traceback.rs`

## Purpose

Decodes the packed Gotoh traceback into gapped alignment rows and computes
alignment metrics.

## Responsibilities

- Walk the packed traceback from a chosen endpoint back to the query start,
  producing ordered `RawColumn` records.
- Build the gapped query and reference strings and the compact operation-run
  string (e.g. `3M1I1M`).
- Count exact matches, mismatches, gap opens, callable columns, and unresolved
  query bases, and derive callable identity.

## Non-responsibilities

No dynamic-programming scoring, strand selection, or variant extraction.

## Key types and functions

- `RawColumn`: one aligned column with query/reference bases and optional
  original indices.
- `RawAlignment`: score, reference span, gapped rows, operation runs, columns,
  and `AlignmentMetrics`.
- `TracebackInput`: the packed trace, dimensions, endpoint, state, and score.
- `decode(input) -> Result<RawAlignment>`: performs the traceback walk.
- `operation_runs(columns) -> (String, usize)`: run-length encodes operations and
  counts gap opens.

## Invariants and errors

- Every traceback index is bounds-checked; overflow or out-of-range access
  returns `Error::Alignment`.
- Reaching a match or deletion state at reference column zero is an error.
- Gapped rows are always equal length; a column is either a match, an insertion
  (query base, reference `-`), or a deletion (query `-`, reference base).
- Callable identity is `exact_matches / callable_columns`, or `0.0` when there
  are no callable columns.

## Dependencies

- `scoring` for `State` and `is_canonical`.
- `model::alignment` for `AlignmentMetrics`.
- `error` for `Error`/`Result`.

## Biological semantics

Callable columns are those where both query and reference bases are canonical;
unresolved query bases (`N`) are counted separately and excluded from identity.
This keeps ambiguous calls from inflating or deflating the reported identity.

## Tests

No dedicated unit tests; behavior is exercised through `gotoh` and `orient`.

## Status

Implemented.
