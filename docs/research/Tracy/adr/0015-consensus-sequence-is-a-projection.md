# ADR-0015: Consensus Sequence Is a Projection, Not the Source of Sample Variants

- **Status:** Accepted for research
- **Date:** 2026-09-18

## Context

Tracy assembly produces a multiple alignment and then collapses columns to a
consensus character string. That representation is convenient, but it loses
support topology, high-quality conflicts, mixed evidence, and detailed indel
support.

Signal's future sample layer needs to preserve those states.

## Decision

The authoritative sample representation shall be aggregated coordinate/event
evidence plus explicit interpretation states.

Sample variants shall derive from that evidence model, not by diffing a
flattened consensus string against the reference.

A consensus sequence may be emitted as a deterministic projection for
interoperability or visualization.

## Consequences

Discordance, mixed evidence, uncovered positions, competing indel placements,
and read provenance remain representable even when no single consensus base
fully describes the sample.
