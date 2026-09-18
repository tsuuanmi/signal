# `src/model/sample_evidence.rs`

## Purpose

Defines internal sample-level scientific evidence after independent read analysis.

## Responsibilities

- Retain every contributing read by reviewer-facing basename plus stable SHA-256 and a concise evidence-derived alignment summary.
- Represent covered reference loci as per-read aligned observations with explicit `reference`, `alternate`, `unresolved`, or `deletion` state.
- Retain normalized canonical variant observations separately from locus observations, with factorized read name/SHA/orientation support, configured eligibility/exclusion reasons, and concise original-call mappings.
- Bind the sample evidence to one reference and one scientific configuration identity.

## Non-responsibilities

No filename/HV/primer-driven placement, F/R pairing, consensus construction, genotype or heteroplasmy inference, variant adjudication, JSON projection, or filesystem I/O.

## Invariants

Absence of a read from one locus means it did not provide a reference-coordinate observation there; it is never converted into reference support. Raw reverse-read bases are not compared directly: locus bases come from the selected alignment on the supplied reference strand.

## Traceability

ADR-0023; `INV-READ-001` through `INV-READ-004`; `SRS-SAMPLE-001` through `SRS-SAMPLE-005`.

## Status

Implemented.
