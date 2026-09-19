# `src/model/sample_evidence.rs`

## Purpose

Defines compact internal sample-level evidence after independent read analysis.

## Responsibilities

- Retain each contributing read once with source basename, stable SHA-256, trace-integrity evidence, and concise evidence-derived post-trim alignment summary.
- Represent maximal reference intervals with constant total/forward/reverse read depth.
- Represent pairwise reference-coordinate overlap/admission evidence without pair-first merging.
- Represent only differential reference loci while preserving every covering read at those retained positions and factor their support by total reads, selected orientation, and reference/alternate/unresolved/deletion state.
- Keep called locus observations as state/base/quality plus one optional reference-oriented `CallSignalEvidence` containing corrected A/C/G/T amplitudes, per-channel SNR, optional basecall-independent `EvidenceProfile`, and existing merged noisy-region membership.
- Represent normalized variant observations with internal deterministic read indexes, eligibility/exclusion reasons, factorized read/eligibility/orientation support topology, and call evidence retaining role, reference-oriented base, co-located four-channel heights, quality, and one required reference-oriented `CallSignalEvidence`; the public report omits the internal quantitative signal context.
- Bind sample evidence to one reference and one scientific configuration identity.

## Non-responsibilities

No filename-driven placement, F/R pairing, consensus, genotype/heteroplasmy inference, JSON read-name projection, or filesystem I/O.

## Invariants

Coverage depth derives only from selected read segments and counts every independently placed read regardless of pairwise eligibility. Internal read indexes address the SHA-sorted registry only inside the domain layer. Pairwise overlap edges use those indexes only after deterministic SHA ordering; non-overlapping reads have no edge. Nucleotide agreement counts canonical base/base observations only, leaving unresolved/gap evidence outside the denominator. Missing coverage is not reference support. Routine all-reference positions are not materialized. At a differential locus, explicit observations include reference supporters as well as alternate, unresolved, or deleted reads. Differential-locus support topology is derived only from those explicit observations; total reads must equal both the forward/reverse partition and the reference/alternate/unresolved/deletion partition. Variant support topology is derived only from per-read observations of that exact normalized variant and cannot absorb covering reference/unresolved/competing-event reads. Call-backed sample signal must resolve from the matching original call's `LocusEvidence`; reverse reads reorder corrected amplitudes and SNRs and complement profile A/T and C/G channels in the same reference-oriented frame. Missing profiles remain missing, noisy-region membership remains observation-only, and deletions have no call signal object.

## Status

Implemented.
