# `src/basecalling/call.rs`

## Purpose

Re-calls every vendor-defined PLOC locus from the analyzed channel signals,
producing a primary sequence plus per-call ambiguity evidence.

## Responsibilities

- Build call windows and per-channel peaks for each PLOC locus.
- Rank channels by peak height and select the primary call, applying the
  configured secondary-peak ratio to identify qualifying channels.
- Emit the primary and IUPAC ambiguity calls with their qualifying channels.
- Retain each call's validated sample-window bounds for downstream
  observation-only signal analysis.
- Record whether the vendor primary agrees with the signal-derived call, without
  retaining duplicate vendor/call fields or using it as the result.

## Non-responsibilities

No ABIF parsing, end trimming, reference alignment, or variant calling.

## Key types and functions

- `call(trace, config) -> Result<BaseCalls>`: the module entry point, re-exported
  from `mod.rs`.

## Invariants and errors

- Calls derive from the four signal channels at validated PLOC loci.
- A non-positive or exactly tied strongest peak yields an unresolved `N` call.
- Qualifying channels are those above the secondary-peak ratio: one channel gives
  a canonical call, two give a two-base IUPAC code, three keep the strongest
  primary with unresolved `N` ambiguity, and four are unresolved `N` for both
  primary and ambiguity.
- The call vector and retained `primary_sequence` have equal lengths; ambiguity is
  retained per call rather than duplicated in a second aggregate string.
- Vendor PBAS is evidence only and never replaces the signal-derived call.

## Dependencies

- `iupac` and `peak`.
- `config` for `BasecallingConfig`.
- `model::basecalls` and `model::trace`.
- `error` for `Result`.

## Biological semantics

The secondary-peak ratio distinguishes a clean single-channel call from a mixed
signal position without inferring genotype. A second channel reaching the ratio
threshold produces a
two-base IUPAC ambiguity; a tie or a non-positive strongest peak is left
unresolved rather than guessed.

## Tests

- `calls_unambiguous_strongest_channel`: a single strong channel yields the
  canonical call.
- `exact_strongest_tie_is_unresolved`: an exact tie between two channels yields
  `N`.
- `three_qualifying_channels_keep_primary_but_not_ambiguity`: three qualifying
  channels keep the strongest primary while the ambiguity is unresolved `N`.
- `four_qualifying_channels_are_fully_unresolved`: four qualifying channels yield
  unresolved `N` for both primary and ambiguity.

## Status

Implemented.
