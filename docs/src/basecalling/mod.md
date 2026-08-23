# `src/basecalling/mod.rs`

## Purpose

Re-calls primary and ambiguous nucleotide calls from chromatogram signals at
validated ABIF PLOC loci.

## Responsibilities

- Re-export `call` as the module boundary.
- Build basecall windows, detect channel peaks, choose primary calls, calculate
  secondary ratios, emit IUPAC ambiguity, and retain trace positions.

## Non-responsibilities

No ABIF parsing, end trimming, reference alignment, or variant calling.

## Key types and functions

- `call(trace, config) -> Result<BaseCalls>`: the public entry point,
  re-exported from `call`.
- Child modules: `iupac` (two-base IUPAC mapping), `peak` (window construction and
  channel peak selection), `call` (call orchestration and ratio thresholding).

## Invariants and errors

Calls derive from the four signal channels at validated PLOC loci. Vendor PBAS
calls are evidence only and never replace the signal-derived call. Output arrays
have validated equal lengths. A tie or non-positive strongest peak yields an
unresolved `N` call; one/two/three qualifying channels produce canonical /
strongest+IUPAC / strongest+unresolved-ambiguity calls, and four produce
unresolved `N` for both primary and ambiguity.

## Dependencies

- `config` for `BasecallingConfig`.
- `model::basecalls`, `model::nucleotide`, `model::trace`.
- `error` for `Result`.

## Apollo mapping

The `peak`, `iupac`, and `basecall` behavior in
`apollo/include/apollo/preprocessing/abif.h`.

## Requirements and decisions

ADR-0003; `SRS-BC-001` through `SRS-BC-005`.

## Tests

Unit tests in `call` cover unambiguous calls and exact-tie resolution. The
end-to-end `tests/analyze.rs` integration tests exercise the full re-calling path.

## Status

Implemented.
