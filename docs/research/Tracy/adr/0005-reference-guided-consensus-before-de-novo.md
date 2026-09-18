# ADR-0005: Prefer Reference-Guided Consensus Before De Novo Assembly

- **Status:** Accepted for research
- **Date:** 2026-09-18

## Context
Tracy supports both reference-guided and de novo assembly. Signal's primary mtDNA use case has a well-defined short reference and already models circular reference coordinates.

## Decision
The first multi-trace/sample implementation shall reconcile reads in reference coordinates. De novo chromatogram assembly remains deferred until a concrete use case demonstrates additional value.

## Consequences
The design reuses existing coordinate/topology rules, simplifies provenance and overlap interpretation, and avoids an unnecessary assembly graph.
