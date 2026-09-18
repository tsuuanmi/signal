# ADR-0012: Candidate Placement Is Not Authoritative Alignment

- **Status:** Accepted for research
- **Date:** 2026-09-18

## Context

Tracy uses exact k-mer/FM-index search to find candidate regions in large
references, then locally refines those candidates with profile-to-sequence
alignment. Public issues document the expected tradeoff: the seed stage is fast
but less sensitive when traces contain Ns, incorrect calls, repeats, or limited
high-quality sequence.

Signal currently does not require large-reference search, but future reference
scope may change.

## Decision

If Signal introduces indexed/seeded reference search, the search stage shall
produce candidate regions only.

Final scientific placement must be established by the authoritative alignment
method with its own scoring, topology, orientation, coordinate, and tie
contracts.

Failure to find a seed hit shall not be described as evidence that no biological
alignment exists.

## Consequences

Search acceleration can evolve independently from scientific alignment.
Sensitivity limitations in the search stage remain diagnosable, and exact
candidate-search heuristics cannot silently redefine variant coordinates.
