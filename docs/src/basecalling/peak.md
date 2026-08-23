# `src/basecalling/peak.rs`

## Purpose

Builds validated basecall windows around each PLOC locus and selects the
strongest positive local peak per channel.

## Responsibilities

- Construct symmetric neighboring-midpoint half-open windows around each PLOC
  position, with edge windows derived from the local spacing.
- For each channel, find the strongest positive local maximum inside the window,
  falling back to the PLOC sample when no positive local maximum exists.

## Non-responsibilities

No ratio thresholding, IUPAC mapping, or call orchestration.

## Key types and functions

- `CallWindow`: a half-open `[start, end)` sample window.
- `windows(trace) -> Result<Vec<CallWindow>>`: builds one window per PLOC locus.
- `peaks(trace, window, ploc) -> [ChannelPeak; 4]`: returns the selected peak for
  each of the four channels.
- `midpoint(left, right) -> Result<usize>`: checked midpoint arithmetic.

## Invariants and errors

- At least two PLOC positions are required; otherwise `Error::Basecalling`.
- Every window must satisfy `start < end`, `end <= sample_count`, and contain its
  PLOC position; violations return `Error::Basecalling`.
- Midpoint overflow returns `Error::Basecalling`.
- A peak is a positive local maximum; when none exists, the PLOC sample is used
  and recorded as `PeakSource::PlocFallback`.

## Dependencies

- `model::basecalls` for `ChannelPeak` and `PeakSource`.
- `model::nucleotide` for `Nucleotide`.
- `model::trace` for `Chromatogram`.
- `error` for `Error`/`Result`.

## Biological semantics

Each PLOC locus is a vendor-identified base position. The window around it
captures the local signal for that base. Selecting the strongest positive local
maximum per channel recovers the peak height used to rank channels and apply the
secondary-peak threshold.

## Tests

- `selects_each_channel_independently_and_falls_back_to_ploc`: verifies independent local maxima and per-channel PLOC fallback.

## Status

Implemented.
