# ADR-0049: Separate descriptive validation datasets from threshold selection

- **Status:** Accepted
- **Date:** 2026-09-19

## Context

The validation corpus now binds approved local AB1 traces, truth/grouping metadata, and
deterministic `signal.validation_locus/v2` measurements. Threshold research needs a
joined analysis dataset, but selecting a cutoff before the real corpus and false-positive
objective are reviewed would turn an implementation convenience into an unsupported
scientific decision.

The corpus can be large: mtDNA validation may contain many cases with thousands of covered
loci and multiple read observations per locus. Analysis tooling therefore cannot assume
that every joined row can be retained as Python objects in memory.

## Decision

Signal provides external local research tooling through
`scripts/analyze_validation_corpus.py` and the `scripts/validation_corpus/research_*`
modules.

The research path:

- accepts only a completed `signal.validation_corpus/v1` directory;
- strictly validates corpus/index identity, case/read metadata, canonical measurement-file
  locations, measurement schema/identity, locus counts, and read provenance;
- streams case-by-case measurement rows into deterministic `loci.csv` and
  `observations.csv` joined tables;
- joins truth, source/holdout grouping, replicate/run/instrument/amplicon metadata, and
  artifact tags without exposing local AB1 paths;
- publishes one no-overwrite `signal.validation_research/v1` index that hash-binds the
  source corpus and both CSV tables;
- computes descriptive distributions for the four current profile-geometry metrics using
  exact empirical nearest-rank percentiles;
- groups descriptive summaries by holdout group, truth class, and
  `include_in_threshold_fit`;
- stores metric samples in compact numeric arrays rather than retaining the joined row
  objects.

This path does **not** choose a candidate threshold, optimize a classifier, inspect a
locked holdout to tune a rule, infer truth, or modify production Signal behavior.

## Consequences

- The local validation corpus has one reproducible dataset-preparation boundary before
  threshold fitting.
- Threshold research can inspect locus-level geometry and read-level event diagnostics
  with the same provenance model.
- Large corpora are processed with bounded row-object memory; exact percentile storage is
  proportional only to the four metric arrays.
- Research outputs remain sensitive ignored artifacts under `validation-results/`.
- A later threshold-selection implementation must require an explicit predeclared
  objective and must be a separate decision/change.

## Non-goals

No LoB/LoD claim, candidate cutoff, ROC-selected rule, heteroplasmy classification,
mixture-fraction estimate, production schema field, or compatibility output is introduced.
