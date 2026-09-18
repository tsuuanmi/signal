# ADR-0009: Treat PLOC as an Explicit External Prior

- **Status:** Accepted for research
- **Date:** 2026-09-18

## Context

Tracy and current Signal both rely on instrument-provided peak locations to
define candidate nucleotide events. Tracy issue #91 demonstrates that a trace
can contain a longer raw/basecall sequence than its usable peak-position series;
Tracy cannot continue basecalling beyond the available peak positions.

## Decision

The PLOC dependency shall remain explicit in the current Signal method.

The pipeline shall conceptually distinguish complete/usable PLOC evidence from
suspicious or incomplete PLOC evidence. A future PLOC-independent event detector
would be a separately versioned basecalling method, not an implicit recovery
path that silently changes semantics.

## Consequences

Failures caused by incomplete instrument analysis can be diagnosed separately
from ordinary low signal. Signal preserves reproducibility while leaving room
for a future waveform-first event detector.
