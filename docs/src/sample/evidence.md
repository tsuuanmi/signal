# `src/sample/evidence.rs`

## Purpose

Aggregates read observations in reference-coordinate and normalized-event space.

## Responsibilities

- Require at least one read and identical reference/configuration identities.
- Reject duplicate trace content so one physical observation cannot be counted twice under different filenames.
- Build deterministic read placements, locus observations, and normalized event support ordered independently of CLI trace order.
- Use alignment-oriented query bases for locus evidence and original call indexes only for trace evidence lookup.

## Locus semantics

Canonical aligned matches are `reference`; canonical mismatches are `alternate`; non-canonical query/reference columns are `unresolved`; alignment deletions are `deletion`. Inserted columns have no reference locus and are represented through normalized event evidence when reportable.

## Non-responsibilities

No majority vote, conflict resolution, consensus, haplogroup inference, or filename/HV/F/R interpretation.

## Tests

Unit tests cover cross-orientation event support, uncovered loci, unresolved and deletion observations, incompatible scientific identities, and duplicate read content.

## Status

Implemented.
