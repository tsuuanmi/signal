# `src/validation/phase_runtime.rs`

## Purpose

Serializes the already-computed production `ReadObservation.phase` evidence into a deterministic validation-only artifact for direct parity comparison with the Python phase research path.

## Responsibilities

- Consume completed `ReadObservation[]` values without invoking phase geometry or measurement code.
- Preserve exact read SHA-256, tract identity, window start/end read-order distance, window call indexes, candidate offsets, informative-position counts, window impurity, and zero/shifted/residual masses.
- Publish `signal.validation_phase_runtime/v1` as `index.json`, `windows.csv`, and `candidates.csv` under `validation-results/<sample-id>.phase-runtime/`.
- Preserve not-applicable and insufficient evidence in `index.json`.
- Hash-bind the two CSV payloads in the artifact index.
- Publish without overwrite and clean up a partially created phase-runtime directory if publication fails.

## Non-responsibilities

No phase geometry, window construction, candidate calculation, thresholding, winning-offset selection, phase state, confidence weighting, variant mutation, sample-policy change, or production/public result serialization.

## Status

Implemented.
