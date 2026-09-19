# `src/model/sample_evidence.rs`

## Purpose

Defines compact internal sample-level evidence after independent read analysis.

## Responsibilities

- Retain each contributing read once with source basename, stable SHA-256, trace-integrity evidence, and concise evidence-derived post-trim alignment summary.
- Represent maximal reference intervals with constant total/forward/reverse read depth.
- Represent pairwise reference-coordinate overlap/admission evidence without pair-first merging.
- Represent only differential reference loci while preserving every covering read at those retained positions.
- Keep called locus observations as state/base/quality plus optional reference-oriented basecall-independent `EvidenceProfile` without public implementation coordinates.
- Represent normalized variant observations with internal deterministic read indexes, eligibility/exclusion reasons, factorized read/eligibility/orientation support topology, and call evidence retaining role, reference-oriented base, co-located four-channel heights, quality, and optional reference-oriented `EvidenceProfile`; the public report omits the profile.
- Bind sample evidence to one reference and one scientific configuration identity.

## Non-responsibilities

No filename-driven placement, F/R pairing, consensus, genotype/heteroplasmy inference, JSON read-name projection, or filesystem I/O.

## Invariants

Coverage depth derives only from selected read segments and counts every independently placed read regardless of pairwise eligibility. Internal read indexes address the SHA-sorted registry only inside the domain layer. Pairwise overlap edges use those indexes only after deterministic SHA ordering; non-overlapping reads have no edge. Nucleotide agreement counts canonical base/base observations only, leaving unresolved/gap evidence outside the denominator. Missing coverage is not reference support. Routine all-reference positions are not materialized. At a differential locus, explicit observations include reference supporters as well as alternate, unresolved, or deleted reads. Variant support topology is derived only from per-read observations of that exact normalized variant and cannot absorb covering reference/unresolved/competing-event reads. Sample profiles must resolve from the matching original call's `LocusEvidence`; reverse reads complement A/T and C/G, missing profiles remain missing, and deletions have no nucleotide profile.

## Status

Implemented.
