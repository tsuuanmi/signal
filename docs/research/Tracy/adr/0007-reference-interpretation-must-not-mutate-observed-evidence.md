# ADR-0007: Reference Interpretation Must Not Mutate Observed Evidence

- **Status:** Accepted for research
- **Date:** 2026-09-18

## Context

Tracy's decomposition algorithm threads the reference through primary and
secondary calls and rewrites those call arrays when a reference-compatible
phasing hypothesis is found. This is effective for constructing two allele
strings, but it mixes observed chromatogram evidence with a downstream
reference-derived interpretation.

Signal's architecture treats scientific evidence and later interpretation as
separate typed stages.

## Decision

Reference-aware algorithms shall not mutate decoded trace data, basecall
evidence, ambiguity evidence, local signal observations, or quality evidence.

A reference-derived correction, phase assignment, decomposition, or consensus
must be represented as a new interpretation object that preserves links back to
the immutable observations that support it.

## Consequences

The same trace evidence can be reinterpreted under different references or
methods without changing its provenance. Debugging and biological review can
distinguish "what the chromatogram showed" from "what the reference-aware model
inferred".
