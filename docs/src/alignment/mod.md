# `src/alignment/mod.rs`

## Purpose

Aligns the retained primary read to the reference sequence using bounded,
deterministic affine-gap Gotoh scoring, and selects the best-supported strand.

## Responsibilities

- Re-export `align_best` as the module boundary.
- Coordinate scoring, traceback, and forward/reverse orientation selection.
- Return the selected internal orientation, score, reference segments, metrics,
  and per-column coordinates without duplicate gapped-row strings.

## Non-responsibilities

No FM-index, multi-contig search, hardcoded HV rescue, variant extraction, or
output formatting.

## Key types and functions

- `align_best(qc, reference, config) -> Result<Alignment>`: the public entry
  point, re-exported from `orient`.
- Child modules: `scoring` (affine scores and state ordering), `gotoh` (DP
  matrices), `traceback` (aligned columns and metrics), `orient` (strand selection
  and coordinate projection).

## Invariants and errors

The complete retained query is consumed; reference flanks may be free. The
selected model retains one ordered column representation rather than duplicate
row strings. Tie order and scores are explicit and deterministic.
Ambiguous orientation or sub-threshold identity returns `Error::Alignment`.

## Dependencies

- `config` for `AlignmentConfig` and `MAX_ALIGNMENT_CELLS`.
- `model::alignment`, `model::nucleotide`, `model::quality`, `model::reference`.
- `error` for `Error`/`Result`.

## Apollo mapping

`apollo/include/apollo/alignment/gotoh.h` and the semi-global configuration used
by Apollo alignment commands.

## Requirements and decisions

ADR-0004; `SRS-ALN-001` through `SRS-ALN-006`.

## Tests

Unit tests in `gotoh` cover free reference flanks and affine gap scoring. The
end-to-end `tests/analyze.rs` integration tests exercise strand selection and
coordinate projection.

## Status

Implemented.
