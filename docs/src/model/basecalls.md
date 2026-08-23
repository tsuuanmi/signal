# `src/model/basecalls.rs`

## Purpose

Defines the signal-derived call records and their peak evidence.

## Responsibilities

- Represent per-channel peaks, the primary/ambiguity calls, qualifying channels,
  and vendor-agreement state needed by downstream analysis.
- Represent the ordered call list and the primary sequence consumed by quality
  control and alignment; ambiguity remains available on each `BaseCall` only.

## Non-responsibilities

No peak detection, ratio thresholding, or call orchestration.

## Key types and functions

- `PeakSource`: `LocalMaximum` or `PlocFallback`.
- `ChannelPeak`: base, height, and source. Selected peak sample position is not
  retained.
- `BaseCall`: original index, PLOC position, sample-window bounds, per-channel
  peaks, primary, ambiguity, qualifying channels, and vendor agreement.
- `BaseCalls`: ordered calls plus `primary_sequence`, with `len()` and
  `is_empty()`; aggregate ambiguity text is not duplicated.

## Invariants and errors

- Every call retains one non-empty 0-based half-open sample window containing
  its PLOC.
- The call vector and primary sequence have equal lengths; each call carries its
  own ambiguity symbol.
- `BaseCalls::len()` equals the number of call loci.

## Dependencies

- `model::nucleotide` for `Nucleotide`.
- `serde` only for serializing the `PeakSource` enum in compact reports.

## Biological semantics

Each call records all four channel peaks and every channel that reached the
ambiguity threshold, capturing clean, mixed, and unresolved positions. The
vendor agreement flag allows quality applicability checks without influencing
the signal-derived result.

## Tests

No dedicated unit tests; behavior is exercised through `basecalling::call`.

## Status

Implemented.
