# `src/sample/differences.rs`

## Purpose

Builds sparse reference-coordinate locus evidence only where at least one read differs from the reference.

## Responsibilities

- Scan selected alignment columns on the supplied reference strand.
- First identify positions with at least one `alternate`, `unresolved`, or `deletion` state.
- Then retain every covering read at those positions, including `reference` observations.
- Preserve original call index and relative quality for called observations.
- Keep deletion observations free of fabricated base/call/quality evidence.
- Keep insertion columns out of reference-coordinate locus evidence.
- Reject duplicate contribution from one read to the same reference coordinate instead of silently duplicating support.

## Sparse semantics

A position inside a read's mapped reference segments but absent from the sample's `locus_differences[]` is a canonical reference match for that read. A position outside the mapped segments is uncovered.

Every retained differential locus contains all covering-read observations so explicit reference support is available exactly where another read differs.

## Non-responsibilities

No normalized variant construction, majority vote, conflict verdict, consensus, genotype, or JSON projection.

## Status

Implemented.
