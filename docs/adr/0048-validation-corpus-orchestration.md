# ADR-0048: Provenance-first local validation corpus orchestration

- **Status:** Accepted
- **Date:** 2026-09-19

## Context

Signal already exposes authoritative all-covered per-locus validation measurements through
`signal-validation`, while validation truth, replicate identity, artifact labels, and
development/holdout grouping intentionally remain outside the Rust scientific core.

Threshold research now needs a repeatable way to execute many validation cases without
turning local manifests into a production input contract or allowing research metadata to
influence read placement. The orchestration layer must also prevent accidental trace reuse,
provenance drift, partial successful studies being mistaken for complete studies, and
overwriting an earlier corpus run.

## Decision

Validation-corpus execution is external Python orchestration under
`scripts/validation_corpus/`, with `scripts/run_validation_corpus.py` as the CLI boundary.

The local CSV manifest uses one row per AB1 trace and must:

- bind every trace to its SHA-256 and exactly one `validation_case_id`;
- preserve source/specimen/PCR/run/instrument/amplicon provenance;
- preserve truth method, optional truth locus/alleles/mixture fraction, artifact tags,
  threshold-fit inclusion, holdout group, approval, redistribution status, and notes;
- reject inconsistent case-level metadata and any source group assigned to multiple
  development/holdout groups;
- treat `declared_direction` only as validation metadata.

For every selected case the runner invokes the authoritative `signal-validation` binary in
an isolated working directory. It validates the generated
`signal.validation_locus/v2` JSONL before accepting it, including schema/sample identity,
strict locus ordering, stable Signal/reference/configuration identity, observation counts,
and read SHA-256 membership.

All selected cases are staged before final publication. The runner then publishes one new,
non-overwriting directory under ignored `validation-results/` containing per-case JSONL,
validation logs, and a deterministic `signal.validation_corpus/v1` index. The index
records manifest/reference/configuration/Signal identity and validation metadata but omits
local AB1 filesystem paths. A case execution or validation failure publishes no final
corpus directory; publication errors roll back the newly created destination.

## Consequences

- Corpus execution is reproducible from explicit hashes and grouping metadata.
- Anti-leakage source grouping is checked before measurements are generated.
- Truth and holdout metadata remain outside production read/sample science.
- Real AB1 files, manifests, logs, measurements, and corpus indexes remain local/ignored
  unless separately approved for redistribution.
- Corpus publication is staged and no-overwrite; it is not a new production result
  contract.

## Non-goals

This decision adds no threshold selection, classifier, heteroplasmy verdict, mixture
quantification, read-placement hint, production result field, or compatibility output.
