# `src/sample/aggregate.rs`

## Purpose

Owns sample-level validation, deterministic read ordering, and assembly of the compact `SampleEvidence` boundary.

## Responsibilities

- Require at least one independently completed `ReadObservation`.
- Require identical reference and configuration identities across all reads.
- Reject duplicate trace content by SHA-256 even when filenames differ.
- Sort reads by SHA-256 so read indexes are deterministic and independent of CLI order.
- Build the one top-level read registry with reviewer-facing basename, stable identity, and selected-alignment summary.
- Delegate sparse differential-locus extraction to `sample::differences`.
- Delegate normalized variant aggregation to `sample::variants`.

## Non-responsibilities

No alignment, variant calling, locus classification details, JSON projection, consensus, conflict adjudication, or metadata-driven pairing.

## Invariants

The 0-based index of a read in the sorted registry is the authoritative reference used by downstream sample evidence. Filename semantics never affect ordering, placement, duplicate identity, or reconciliation.

## Tests

Unit tests cover deterministic ordering, indexed evidence, sparse all-reference overlap, explicit reference support at differential loci, filtered variant retention, duplicate normalized support rejection, incompatible scientific identities, and renamed duplicate content.

## Status

Implemented.
