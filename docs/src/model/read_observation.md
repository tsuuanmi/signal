# `src/model/read_observation.rs`

## Purpose

Defines the complete scientific observation produced from one independently processed read after reference placement.

## Responsibilities

- Group input, reference, and configuration identities with signal-derived calls, signal-quality observations, quality-control result, selected alignment, and read-level variants for one read.
- Establish the explicit boundary between one-read processing and future sample-level reconciliation.
- Preserve evidence-derived orientation and mapped reference segments from the selected alignment.
- Keep assay names, primer labels, filenames, declared direction, and canonical F/R pairing outside the scientific placement model.

## Non-responsibilities

No sample consensus, cross-read conflict resolution, amplicon classification, metadata-driven placement, filesystem access, or reporting policy.

## Key type

- `ReadObservation`: immutable ownership bundle for one admitted read's scientific products.\n- `is_compatible_with`: requires identical reference and scientific configuration identities.\n- `overlaps_reference`: detects coordinate overlap only between compatible observations, including circular split segments.

## Invariants

- A read is processed independently before any sample-level reconciliation.
- Covered reference region and orientation are consequences of alignment evidence.
- Optional assay metadata may be used later for provenance or post-mapping QC, but does not alter the observation's scientific placement.
- Missing canonical F/R partners do not invalidate an otherwise usable read.

## Dependencies

Validated model types only: base calls, signal analysis, quality control, alignment, and variant-calling result.

## Traceability

ADR-0023; `INV-READ-001` through `INV-READ-004`; `SRS-ALN-007` through `SRS-ALN-009`.

## Status

Implemented as the one-read boundary; sample-level aggregation remains future work.
