# `src/phase/geometry.rs`

## Purpose

Owns canonical circular-rCRS applicability and HV1/HV2 tract geometry for
`signal.polyc_phase/v1`.

## Responsibilities

- Verify circular topology, exact normalized rCRS sequence identity, length, and tract
  sequences.
- Define canonical HV2/HV1 tract coordinates and interrupt positions.
- Compute positive post-tract reference distance in selected sequencing orientation with
  rCRS origin wrap.

## Non-responsibilities

No alignment selection, signal/profile extraction, candidate mass aggregation, generic
homopolymer detection, or biological tract interpretation.

## Traceability

ADR-0055, ADR-0056, SRS-PHASE-002.
