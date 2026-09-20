# `src/phase/mod.rs`

## Purpose

Owns the current internal `signal.polyc_phase/v1` method boundary and method constants.

## Responsibilities

- Fix the v1 25-profile window size, stride 5, and ±1..±5 candidate offsets.
- Expose the one authoritative read-local measurement entry point.
- Keep geometry and measurement implementation private to the phase module.

## Non-responsibilities

No configuration parsing, public reporting, sample reconciliation, phase-state
classification, or reliability policy.

## Traceability

ADR-0055 and ADR-0056.
