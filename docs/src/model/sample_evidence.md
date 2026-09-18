# `src/model/sample_evidence.rs`

## Purpose

Defines compact internal sample-level evidence after independent read analysis.

## Responsibilities

- Retain each contributing read once with reviewer-facing basename, stable SHA-256, and concise evidence-derived alignment summary.
- Represent only differential reference loci while preserving every covering read at those retained positions.
- Represent normalized canonical variant observations with deterministic read indexes, eligibility/exclusion reasons, and concise original-call mappings.
- Bind sample evidence to one reference and one scientific configuration identity.

## Non-responsibilities

No filename/HV/primer-driven placement, F/R pairing, consensus construction, genotype or heteroplasmy inference, variant adjudication, JSON projection, or filesystem I/O.

## Invariants

Read indexes address the SHA-sorted read registry. Missing coverage is not reference support. Routine all-reference positions are not materialized. At a differential locus, explicit observations include reference supporters as well as alternate, unresolved, or deleted reads.

## Traceability

ADR-0023, ADR-0025; `INV-READ-001` through `INV-READ-004`; `INV-SAMPLE-001` through `INV-SAMPLE-006`.

## Status

Implemented.
