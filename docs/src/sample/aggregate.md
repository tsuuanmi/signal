# `src/sample/aggregate.rs`

## Purpose

Owns sample-level validation, deterministic read ordering, and assembly of compact `SampleEvidence`.

## Responsibilities

- Require at least one independently completed read.
- Require identical reference/configuration identities.
- Reject duplicate trace content by SHA-256 even when filenames differ.
- Sort reads by SHA-256 so internal registry indexes are deterministic and independent of CLI order.
- Build the one top-level read registry with source basename, stable identity, and selected post-trim alignment summary.
- Consume the validated `SampleReconciliationConfig`.
- Delegate pairwise overlap admission, sparse differential-locus extraction, and normalized variant aggregation.

## Non-responsibilities

No filename-driven placement, pair-first merging, JSON filename-stem projection, consensus, or sample-level conflict adjudication.

## Invariants

Internal indexes are deterministic implementation references only. Public reviewer-facing read names are produced later by the report layer and do not influence scientific ordering or placement.

## Tests

Unit tests cover deterministic SHA ordering with overlap indexes bound to that registry, sparse all-reference overlap, explicit reference support at differential loci, filtered variant retention, duplicate locus/variant support rejection, incompatible identities, and renamed duplicate content.

## Status

Implemented.
