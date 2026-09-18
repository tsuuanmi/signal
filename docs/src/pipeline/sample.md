# `src/pipeline/sample.rs`

## Purpose

Runs one multi-read sample-evidence operation.

## Responsibilities

- Load one validated sample identifier, one shared reference/configuration, and one or more traces.
- Process every trace independently through `pipeline::observation`.
- Aggregate completed observations through `sample::aggregate`.
- Log read, sparse differential-locus, and normalized-variant counts.
- Build and atomically publish one `signal.sample_evidence/v2` document at `results/<sample-id>.sample.json`.
- Write sample-level operational records to `$SIGNAL_LOG_DIR/<sample-id>.sample.log`.

## Non-responsibilities

No F/R pairing, metadata-derived placement, consensus calling, sample-level variant adjudication, or per-read v5 publication.

## Status

Implemented.
