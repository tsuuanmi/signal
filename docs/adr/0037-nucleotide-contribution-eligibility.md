# ADR-0037: Define structural nucleotide contribution eligibility

- **Status:** Accepted
- **Date:** 2026-09-19

## Context

Signal now preserves local coverage, overlap admission, support topology,
reference-oriented `EvidenceProfile`, and observation-only noisy-region context
at sample scope.

The next consensus boundary needs an explicit answer to a narrower question
before any weighting policy is introduced:

> Does this retained locus observation contain actual nucleotide-profile evidence
> that can participate in a future nucleotide aggregation?

Using relative quality or `candidate_noisy` as a hard gate here would introduce
new scientific semantics that are not calibrated for consensus. Conversely,
treating zero-signal loci or deletions as nucleotide observations would fabricate
evidence.

## Decision

Each retained differential-locus observation receives one internal
`NucleotideContribution` state:

~~~text
Eligible
MissingProfile
DeletionEvent
~~~

Rules are deterministic:

~~~text
deletion
    -> DeletionEvent

call-backed observation + EvidenceProfile
    -> Eligible

call-backed observation + no EvidenceProfile
    -> MissingProfile
~~~

An unresolved/IUPAC primary call with a real `EvidenceProfile` remains
`Eligible`: the profile, not the collapsed character, is the nucleotide
evidence.

Candidate-noisy-region membership and uncalibrated relative quality remain
context only and MUST NOT change this eligibility state.

Each differential locus also derives:

~~~text
nucleotide_eligible_reads
eligible_forward_reads
eligible_reverse_reads
~~~

with:

~~~text
nucleotide_eligible_reads
    = eligible_forward_reads + eligible_reverse_reads
~~~

The current public `signal.sample_evidence/v7` contract remains unchanged.
Production logs consume eligible and missing-profile counts.

## Consequences

- Future consensus has an explicit nucleotide contributor denominator.
- Zero-signal loci do not gain fabricated one-hot or reference support.
- Mixed/unresolved calls can still contribute their preserved profile evidence.
- Deletions stay separate from nucleotide support and future gap/event policy.
- No threshold, down-weighting, consensus vote, confidence, genotype, or
  heteroplasmy semantics are introduced.

## Non-goals

This decision does not define quality-aware weighting, noisy-tail suppression,
artifact-aware local rejection, gap confidence, consensus states, or sample-level
variant calling.
