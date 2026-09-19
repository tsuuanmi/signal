# `src/signal_processing/locus_evidence.rs`

## Purpose

Derives one basecall-independent `LocusEvidence` record for every validated PLOC locus.

## Responsibilities

- Derive both the locus window and fixed-width local-statistics context from shared PLOC geometry, without consuming basecall records or rolling noisy-window records.
- Estimate per-channel local baseline and noise.
- Refine the event sample by maximizing total baseline-corrected A/C/G/T signal inside the locus window.
- Resolve event-score ties by nearest PLOC and then lower sample coordinate.
- Derive raw co-located heights, corrected amplitudes, SNR, and normalized evidence profile directly from chromatogram channels.

## Non-responsibilities

No use of primary calls, ambiguity codes, selected basecall peaks, qualifying-channel membership, alignment, variant filtering, or biological mixture interpretation.

## Tests

Tests cover context placement, unresolved/basecall-independent loci, mixed-channel mass retention, deterministic event refinement, and zero-signal loci.

## Status

Implemented.
