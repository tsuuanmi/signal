# ADR-0044: Separate validation measurements from public sample evidence

- **Status:** Accepted
- **Date:** 2026-09-19

## Context

Threshold research requires per-locus geometry from clean reference-matching loci as well
as differential loci. The public `signal.sample_evidence/v7` contract is intentionally sparse
and omits internal nucleotide-profile geometry, while aggregate logs are insufficient for
threshold fitting.

Adding research-only fields to the production sample schema would couple exploratory
calibration to a stable scientific result contract. Exporting only sparse differential loci
would bias the null distribution by removing clean reference-matching positions.

## Decision

Signal provides a separate `signal-validation` binary for local validation measurement
export.

The validation path:

- uses the same trace decoding, basecalling, signal processing, QC, alignment, variant
  calling, sample compatibility validation, and nucleotide-profile geometry as production;
- shares one generic sample-locus builder with production;
- selects all covered reference loci for validation, while production selects differential
  loci only;
- emits deterministic `signal.validation_locus/v1` JSONL under
  `validation-results/<sample-id>.jsonl`;
- publishes atomically without overwrite;
- never applies a candidate threshold or biological interpretation;
- does not change `signal.sample_evidence/v7`.

Validation truth labels and prepared mixture fractions remain external metadata and are
joined during analysis rather than inferred by Signal.

## Consequences

- Clean homoplasmic loci are available for empirical null distributions.
- Threshold research and public result compatibility remain independent.
- There is one authoritative locus observation/geometry implementation.
- Validation exports inherit source-data privacy requirements and remain ignored local
  artifacts.

## Non-goals

No threshold selection, classifier, heteroplasmy call, LoD/LoQ claim, production schema
field, or compatibility output is introduced.
