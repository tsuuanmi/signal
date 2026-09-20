# `src/model/phase.rs`

## Purpose

Defines the internal vocabulary for continuous read-local mtDNA poly-C phase evidence.

## Responsibilities

- Represent reference applicability separately from phase interpretation.
- Represent explicit insufficient-evidence reasons.
- Preserve one record per supported tract.
- Preserve exact profile-bearing windows and the complete non-zero candidate-offset curve.
- Preserve shifted/zero/residual masses without selecting a winner or assigning a state.

## Non-responsibilities

No detector threshold, phase classification, confidence, sample weighting, no-call,
variant interpretation, serialization, configuration, or filesystem behavior.

## Key types

- `ReadPhaseEvidence`
- `PhaseApplicability`
- `PhaseTractEvidence`
- `PhaseEvidenceAvailability`
- `PhaseInsufficiency`
- `PhaseWindowEvidence`
- `PhaseCandidateEvidence`

## Traceability

ADR-0055, ADR-0056, SRS-PHASE-001 through SRS-PHASE-007.
