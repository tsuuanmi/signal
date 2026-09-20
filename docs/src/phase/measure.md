# `src/phase/measure.rs`

## Purpose

Computes continuous read-local post-poly-C candidate evidence from an already selected
alignment and immutable signal profiles.

## Responsibilities

- Project call-backed profiles into reference A/C/G/T orientation.
- Verify exact tract representation in the selected alignment.
- Derive tract call span from original call indexes.
- Identify post-tract observations from actual read history.
- Build exact 25-profile windows with stride 5.
- Evaluate every ±1..±5 candidate using local represented reference geometry.
- Retain zero-reference, shifted-reference, and residual mass plus explicit
  insufficient-evidence states.

## Non-responsibilities

No winning offset, `PhaseState`, recovery rule, confidence/weight, variant mutation,
sample pairing, public output, or configuration.

## Traceability

ADR-0054, ADR-0055, ADR-0056; SRS-PHASE-001 through SRS-PHASE-006.
