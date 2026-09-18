# ADR-0024: Reference-coordinate sample evidence contract

- **Status:** Accepted
- **Date:** 2026-09-18

## Context

ADR-0023 established `ReadObservation` as the one-read boundary and required future
sample reconciliation to operate in mapped reference-coordinate/event space rather
than canonical F/R pairs. Real mtDNA sample output confirms the need for that
boundary: reverse reads retain raw trace-strand bases that differ from their
reference-strand normalized variants, non-canonical assay pairs can overlap, and
absence from a read's reported variant list does not prove reference support.

## Decision

Signal adds a separate sample operation:

`signal sample <sample-id> <trace.ab1>... --reference <reference.fasta>`

Every trace is independently processed through the same `pipeline::observation`
path used by single-read `analyze`. Only completed `ReadObservation` values enter
sample aggregation.

Sample evidence has two complementary layers:

1. **Locus observations** come directly from selected alignment columns on the
   supplied reference strand. Covered loci are classified as `reference`,
   `alternate`, `unresolved`, or `deletion`, with original call index and
   relative quality retained when a query call exists.
2. **Normalized events** aggregate only reportable read-level variants by
   biological `(position, reference, alternate, kind)` identity and retain every
   supporting read SHA-256 plus derived orientation.

A read absent from a locus contributes no observation and never counts as
reference support. Inserted query columns have no reference locus and are handled
through normalized event evidence. Duplicate trace content is rejected so copied
files cannot be counted twice.

The public contract is `signal.sample_evidence/v1`, published atomically as
`results/<sample-id>.sample.json`. The sample identifier affects naming and
provenance only; it never affects placement or scientific reconciliation.

## Consequences

- F/R, HV, primer, replicate, and filename labels are unnecessary for placement
  and event merging.
- Forward and reverse observations are directly comparable because
  `AlignmentColumn.query_base` is already oriented to the reference strand.
- Low-quality/excluded read-level differences remain visible as locus observations
  but do not become normalized event support.
- The evidence contract is intentionally not a consensus or sample-variant
  interpretation contract.

## Non-goals

No consensus sequence, majority voting, conflict adjudication, haplogroup
interpretation, heteroplasmy/genotype inference, metadata-driven placement,
canonical F/R pair object, or compatibility alias is introduced.
