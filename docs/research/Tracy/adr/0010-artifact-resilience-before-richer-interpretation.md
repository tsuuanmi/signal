# ADR-0010: Validate Artifact Resilience Before Richer Interpretation

- **Status:** Accepted for research
- **Date:** 2026-09-18

## Context

Tracy issue #116 documents failure on high-amplitude dye-blob-like artifacts.
A very large local artifact can dominate ordinary peak comparison even when
usable lower-amplitude sequence remains visible elsewhere.

Evidence profiles and profile-aware alignment can make downstream reasoning more
expressive, but they cannot recover evidence that the upstream caller or event
model has already mischaracterized.

## Decision

Before profile-aware alignment is promoted into production, Signal shall
validate the upstream locus evidence model against high-amplitude artifacts,
saturation/clipping, baseline shifts, and neighboring-event interference.

Artifact observations shall use local robust evidence where possible and shall
remain distinct from biological mixed-signal interpretation.

## Consequences

Profile work is gated by evidence quality rather than architectural enthusiasm.
The research plan must include controlled artifact cases and a real approved
corpus when available.
