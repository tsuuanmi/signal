# `src/alignment/scoring.rs`

## Purpose

Defines the affine scoring model and deterministic state ordering used by the
Gotoh dynamic program.

## Responsibilities

- Provide the `NEGATIVE_INFINITY` sentinel and sentinel-preserving 64-bit score arithmetic.
- Classify substitution scores: canonical match, canonical mismatch, or the
  ambiguous score when either base is non-canonical.
- Define the `Match`/`Insertion`/`Deletion` state enum and its bit encoding used
  by the packed traceback.

## Non-responsibilities

No dynamic programming, traceback, strand selection, or configuration loading.

## Key types and functions

- `State` enum: `Match`, `Insertion`, `Deletion`, with `from_bits` decoding the
  packed traceback bits.
- `substitution(query, reference, config) -> i64`: returns the configured score
  for a column, widened to `i64`.
- `is_canonical(base) -> bool`: true for `A`/`C`/`G`/`T`.
- `add(score, delta) -> i64`: 64-bit addition that preserves the
  `NEGATIVE_INFINITY` sentinel.

## Invariants and errors

- `NEGATIVE_INFINITY` is `i64::MIN / 4`; `add` preserves it instead of applying
  a configured score delta.
- Finite alignment scores cannot overflow `i64` under the input-size and
  100-million-cell caps when each configured delta is an `i32`.
- `State::from_bits` maps any unrecognized bits to `Match`.
- Alignment scores are `i64`; the configured `match`/`mismatch`/`ambiguous`/gap
  score deltas remain `i32` and are widened at scoring time.

## Dependencies

- `config` for `AlignmentConfig`.

## Biological semantics

Canonical bases score as match or mismatch; any column involving an ambiguous or
unresolved base (`N` or IUPAC) receives the configured `ambiguous_score`, which is
typically neutral so unresolved calls do not dominate the alignment.

## Tests

No dedicated unit tests; behavior is exercised through `gotoh` and `traceback`.

## Status

Implemented.
