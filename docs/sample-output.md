# Signal Sample Evidence JSON

`signal sample <sample-id> <trace.ab1>... --reference <reference.fasta>`
writes one deterministic `results/<sample-id>.sample.json` document identified as
`signal.sample_evidence/v1`. The authoritative schema is
[`schemas/sample-evidence-v1.schema.json`](schemas/sample-evidence-v1.schema.json)
and the example is
[`examples/sample-evidence-v1.example.json`](examples/sample-evidence-v1.example.json).

The sample identifier is validated naming/provenance data only. It does not
constrain read placement, orientation, overlap, or variant reconciliation.

## Reads

`reads[]` contains one record per unique input SHA-256. `name` is the UTF-8 AB1 basename retained for reviewer-facing provenance; `sha256` remains the stable content identity. The nested `alignment` object contains the evidence-derived orientation, callable-base count, callable identity, mismatch count, gap-open count, unresolved-base count, one or two 0-based half-open reference segments, and origin-wrap status. Records are sorted by SHA-256, so input argument order does not change the scientific ordering. Renaming an input changes provenance display only; it does not affect placement or reconciliation.

## Loci

`loci[]` contains only reference positions observed by at least one aligned read.
Each locus has a 1-based `position`, the reference base, and one or more read
observations.

Observation states are:

- `reference`: canonical aligned query base equals the reference base;
- `alternate`: canonical aligned query base differs from the reference base;
- `unresolved`: query or reference base is not canonically comparable;
- `deletion`: the selected alignment contains a query gap at that reference base.

Every locus observation retains `read_name` plus `read_sha256`, so reviewers can identify the contributing file without using filenames as scientific keys. Non-deletion observations retain the reference-oriented aligned `base`, original 0-based call `index`, and uncalibrated `relative_quality`. Deletions do not fabricate call or quality evidence.

A read absent from a locus contributes no observation. Absence is uncovered
evidence, never implicit reference support.

## Variants

`variants[]` aggregates normalized canonical read-level observations by
`(position, reference, alternate, kind)` before configured eligibility removes
them from the single-read report. Each support record contains `read_name`, `read_sha256`, the derived orientation, an `eligible` flag, the exact configured `exclusion_reasons`, and concise `calls[]` pointers. A call pointer carries its role, original 0-based call `index`, optional 1-based aligned reference `position`, and 0-based ABIF `ploc`, allowing a reviewer to drill into the corresponding per-read analysis without duplicating chromatogram payloads.

An eligible support has an empty exclusion list. An ineligible support retains one
or more reasons such as `outside_configured_region`,
`peak_below_minimum`, or
`relative_quality_not_above_threshold`. Thus a normalized variant observed by two
reads remains a two-read observation even if only one read satisfies reporting
thresholds.

Locus evidence and variant evidence intentionally answer different questions.
`loci[]` preserves aligned reference-position observations, including canonical
mismatches that cannot become a normalized/reportable event. `variants[]` preserves
normalized canonical variant identity plus per-read eligibility. Non-canonical or
over-limit differences that cannot form a valid normalized variant remain exclusion
diagnostics rather than fabricated variant records.

## Non-goals

The v1 contract contains no consensus sequence, sample-level adjudicated variant verdict,
majority-vote result, genotype, heteroplasmy estimate, haplogroup interpretation,
F/R pair object, primer/HV label, or filename-derived placement.
