# ADR-0003: Layer Sample Analysis Above the Single-Trace Core

- **Status:** Accepted for research
- **Date:** 2026-09-18

## Context
Forward/reverse consensus and multi-amplicon analysis require multiple traces, while Signal deliberately processes one trace per core invocation.

## Decision
Sample-level reconciliation shall consume completed single-trace observations. Low-level basecalling, signal processing, quality control, alignment, and variant modules shall not become collection-oriented merely to support consensus.

## Consequences
The single-trace pipeline remains independently testable and auditable. Sample-level provenance can explicitly track contributing traces and conflicts.
