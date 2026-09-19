# `src/model/sample_evidence.rs`

## Purpose

Defines compact internal sample-level evidence after independent read analysis.

## Responsibilities

- Retain each contributing read once with source basename, stable SHA-256, and concise evidence-derived post-trim alignment summary.
- Represent pairwise reference-coordinate overlap/admission evidence without pair-first merging.
- Represent only differential reference loci while preserving every covering read at those retained positions.
- Keep called locus observations as state/base/quality without public implementation coordinates.
- Represent normalized variant observations with internal deterministic read indexes, eligibility/exclusion reasons, and reviewer-facing call evidence: role, reference-oriented base, co-located four-channel heights, and quality.
- Bind sample evidence to one reference and one scientific configuration identity.

## Non-responsibilities

No filename-driven placement, F/R pairing, consensus, genotype/heteroplasmy inference, JSON read-name projection, or filesystem I/O.

## Invariants

Internal read indexes address the SHA-sorted registry only inside the domain layer. Pairwise overlap edges use those indexes only after deterministic SHA ordering; non-overlapping reads have no edge. Nucleotide agreement counts canonical base/base observations only, leaving unresolved/gap evidence outside the denominator. Missing coverage is not reference support. Routine all-reference positions are not materialized. At a differential locus, explicit observations include reference supporters as well as alternate, unresolved, or deleted reads.

## Status

Implemented.
