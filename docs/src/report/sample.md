# `src/report/sample.rs`

## Purpose

Projects internal `SampleEvidence` into `signal.sample_evidence/v3`.

## Responsibilities

- Validate evidence/reference identity.
- Convert each source basename to a reviewer-facing filename stem.
- Require those stems to be unique within one sample result.
- Keep SHA-256 as the stable scientific content identity.
- Resolve internal read indexes to human-readable read names in sparse locus and variant evidence.
- Project post-trim alignment summaries, locus state/base/quality, and variant role/base/peaks/quality.
- Reuse shared `AlignmentResult` and `PeakHeightsResult` types.

## Non-responsibilities

No scientific placement, aggregation, consensus, or filesystem publication.

## Status

Implemented.
