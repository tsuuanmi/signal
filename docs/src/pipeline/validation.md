# `src/pipeline/validation.rs`

## Purpose

Exports deterministic local per-locus measurements for empirical validation and threshold research.

## Responsibilities

- Load validation traces/reference/config through the same input path used by `sample`.
- Reuse `sample_reads` and production sample aggregation to validate the complete read set.
- Request all-covered locus evidence from the authoritative sample-locus builder.
- Log aggregate internal phase-evidence applicability, availability, and window coverage for validation runs without changing the validation JSONL schema.
- Publish the already-computed `ReadObservation.phase` values through `signal.validation_phase_runtime/v1` without invoking phase geometry or measurement code.
- Serialize one `signal.validation_locus/v2` JSON object per covered locus in deterministic position order, including one strict per-read diagnostic record that exposes existing call/PLOC/primary-peak/signal-event provenance and reference-oriented channel evidence.
- Publish the existing locus JSONL without overwrite to `validation-results/<sample-id>.jsonl` and the separate phase-runtime artifact under `validation-results/<sample-id>.phase-runtime/`.
- Keep truth labels and candidate thresholds outside the exporter.

## Non-responsibilities

No production schema mutation, threshold fitting, biological classification, heteroplasmy estimation, or truth inference.

## Status

Implemented.
