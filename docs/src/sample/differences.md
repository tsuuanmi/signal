# `src/sample/differences.rs`

## Purpose

Builds sparse reference-coordinate evidence only where at least one read differs from the reference.

## Responsibilities

- First identify positions with at least one `alternate`, `unresolved`, or `deletion` state.
- Then retain every covering read at those positions, including `reference` observations.
- Preserve reference-oriented observed base and uncalibrated quality plus one coherent `CallSignalEvidence` for every called observation.
- Resolve the matching `LocusEvidence` once by original call index and project corrected amplitudes, SNRs, optional profile weights, and noisy-region membership into one reference-oriented signal object.
- Preserve a valid missing/zero-signal profile inside that object without called-base or reference fallback.
- Keep deletions free of fabricated base/quality/call-signal evidence.
- Keep insertion columns out of reference-coordinate locus evidence.
- Reject duplicate contribution from one read to the same reference coordinate.
- Derive one internal support topology per retained locus: total reads, forward/reverse reads, and reference/alternate/unresolved/deletion reads, with both partitions required to sum to total reads.

## Sparse semantics

Inside mapped post-trim coverage, absence from `locus_differences[]` means canonical reference match. Outside mapped segments means uncovered.

## Status

Implemented.
