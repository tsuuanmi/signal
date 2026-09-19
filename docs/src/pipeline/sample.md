# `src/pipeline/sample.rs`

## Purpose

Runs one multi-read sample-evidence operation.

## Responsibilities

- Load one validated sample identifier, one shared reference/configuration, and one or more traces.
- Process every trace independently through `pipeline::observation`.
- Aggregate completed observations through `sample::aggregate` using the strict sample-reconciliation overlap policy.
- Log read, coverage-segment, pairwise-overlap/admission, sparse differential-locus, normalized-variant, and retained profile counts; support topology remains inside each normalized variant rather than a separate operational verdict.
- Build and atomically publish one `signal.sample_evidence/v7` document at `results/<sample-id>.sample.json`.
- Write sample-level operational records to `$SIGNAL_LOG_DIR/<sample-id>.sample.log`.

## Non-responsibilities

No F/R pairing, metadata-derived placement, consensus calling, sample-level variant adjudication, or per-read compatibility publication.

## Status

Implemented.
