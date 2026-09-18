# ADR-0008: Consensus Must Remain Evidence- and Gap-Aware

- **Status:** Accepted for research
- **Date:** 2026-09-18

## Context

Tracy uses rich trace profiles during pairwise and progressive alignment, but
multi-trace assembly ultimately calls MSA columns by character majority. Public
issues confirm that assembly does not use per-base quality and that base-versus-
gap ties can be resolved by deterministic convention rather than evidence.

For Signal, a sample consensus will eventually combine forward, reverse,
replicate, and overlapping-amplicon observations.

## Decision

Signal sample consensus shall not reduce admitted observations to unweighted
character voting before the final locus decision.

Consensus must retain, as applicable:

- per-observation nucleotide evidence;
- trace/call provenance;
- orientation and independent-strand support;
- local quality/evidence state;
- gap/insertion/deletion event evidence;
- conflicting high-quality alternatives;
- local coverage denominator.

Gap support shall be modeled explicitly rather than assigned a fabricated
nucleotide-like quality.

## Consequences

Consensus is more complex than majority voting, but the result remains auditable
and does not discard exactly the evidence that profile-aware alignment was
introduced to preserve.
