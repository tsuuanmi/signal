# `src/sample/contribution.rs`

## Purpose

Defines the first explicit per-locus nucleotide-contribution eligibility boundary
for future sample interpretation.

## Responsibilities

- Classify a retained locus observation as `Eligible`, `MissingProfile`, or
  `DeletionEvent`.
- Treat any call-backed observation with a real basecall-independent
  `EvidenceProfile` as nucleotide-eligible, including unresolved calls.
- Keep zero-signal/missing-profile observations out of nucleotide aggregation.
- Keep deletions on the separate gap/event evidence path.

## Non-responsibilities

No quality threshold, noisy-region rejection, read admission, profile weighting,
consensus base, confidence score, variant verdict, genotype, or heteroplasmy
inference.

## Invariants

Eligibility depends only on whether actual nucleotide-profile evidence exists
for a call-backed observation. Existing relative quality and candidate-noisy
context remain preserved evidence but do not alter this eligibility state.

## Status

Implemented.
