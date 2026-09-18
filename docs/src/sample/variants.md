# `src/sample/variants.rs`

## Purpose

Aggregates normalized read-level variant observations into deterministic sample variant evidence.

## Responsibilities

- Group normalized observed variants by biological `(position, reference, alternate, kind)` identity.
- Preserve the deterministic top-level read index for each contributing read.
- Preserve configured eligibility and exact exclusion reasons without dropping filtered observations.
- Map each normalized observation back to concise original-call role/index/reference-position/PLOC evidence.

## Non-responsibilities

No read placement, locus classification, genotype/heteroplasmy inference, consensus, conflict adjudication, or filesystem/reporting logic.

## Invariants

Read metadata is not repeated here. The support `read` index resolves through the SHA-sorted sample read registry. Read-level filtering changes eligibility, not whether the normalized observation exists.

## Status

Implemented.
