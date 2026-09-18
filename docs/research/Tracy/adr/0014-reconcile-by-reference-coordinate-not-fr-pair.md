# ADR-0014: Reconcile Reads by Reference Coordinate and Event, Not by F/R Pair

- **Status:** Accepted for research
- **Date:** 2026-09-18

## Context

A tiled Sanger sample may contain canonical forward/reverse pairs, but overlaps
also occur across different amplicons. For example HV2F and HV3R may observe
the same mtDNA coordinates even though they are not one named pair.

Merging each F/R pair into an intermediate amplicon consensus would discard
read-level support topology before cross-amplicon reconciliation.

## Decision

Sample reconciliation shall aggregate all admitted ReadObservation values in
reference-coordinate/event space.

Direction, amplicon, primer, and replicate relationships remain provenance and
support dimensions. They shall not define exclusive merge pairs.

Missing a canonical partner read shall not prevent other overlapping reads from
contributing.

## Consequences

Same-amplicon F/R support and cross-amplicon overlap are handled by one model.
Every sample locus can report the actual contributing read/direction/amplicon
topology without pair-first information loss.
