# ADR-0004: Do Not Port Diploid Semantics to mtDNA

- **Status:** Accepted for research
- **Date:** 2026-09-18

## Context
Tracy's decomposition work is useful for detecting persistent mixed signal and post-indel phase changes, but its biological interpretation targets diploid/two-allele use cases. mtDNA secondary signal can have several biological and technical causes.

## Decision
Signal research may reuse lower-level mixed-signal and breakpoint mechanisms, but shall not automatically translate them into heterozygous genotype, two-allele decomposition, or heteroplasmy fraction claims.

## Consequences
Early outputs remain evidence or unresolved hypotheses. Heteroplasmy estimates require controlled mixtures, independent truth, calibration, and assay-specific limits of detection.
