# ADR-0001: Preserve Evidence Beyond Primary Calls

- **Status:** Accepted for research
- **Date:** 2026-09-18

## Context
Signal retains richer per-call chromatogram evidence than its primary-sequence alignment consumes. Tracy demonstrates that nucleotide profiles can remain useful through alignment and consensus.

## Decision
Treat the primary call as one interpretation of a locus, not the only downstream representation. Future profile and sample-level work must retain explicit A/C/G/T evidence and original call/sample mappings.

## Consequences
Alignment and consensus can consume richer evidence while primary sequence remains a stable baseline/projection. New evidence types require deterministic normalization and validation.
