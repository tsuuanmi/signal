# Signal Sample Evidence JSON

`signal sample <sample-id> <trace.ab1>... --reference <reference.fasta>`
writes one deterministic `results/<sample-id>.sample.json` document identified as
`signal.sample_evidence/v1`. The authoritative schema is
[`schemas/sample-evidence-v1.schema.json`](schemas/sample-evidence-v1.schema.json)
and the example is
[`examples/sample-evidence-v1.example.json`](examples/sample-evidence-v1.example.json).

The sample identifier is validated naming/provenance data only. It does not
constrain read placement, orientation, overlap, or event reconciliation.

## Reads

`reads[]` contains one record per unique input SHA-256 with its evidence-derived
orientation, one or two 0-based half-open reference segments, and origin-wrap
status. Records are sorted by SHA-256, so input argument order does not change the
scientific document.

## Loci

`loci[]` contains only reference positions observed by at least one aligned read.
Each locus has a 1-based `position`, the reference base, and one or more read
observations.

Observation states are:

- `reference`: canonical aligned query base equals the reference base;
- `alternate`: canonical aligned query base differs from the reference base;
- `unresolved`: query or reference base is not canonically comparable;
- `deletion`: the selected alignment contains a query gap at that reference base.

Non-deletion observations retain the reference-oriented aligned `base`, original
0-based call `index`, and uncalibrated `relative_quality`. Deletions do not
fabricate call or quality evidence.

A read absent from a locus contributes no observation. Absence is uncovered
evidence, never implicit reference support.

## Events

`events[]` aggregates only normalized reportable read-level variants by
`(position, reference, alternate, kind)`. Each support record contains the input
SHA-256 and the selected orientation of one contributing read.

Locus evidence and event evidence intentionally answer different questions. A
canonical mismatch may remain visible as an aligned `alternate` locus observation
even when read-level variant eligibility filters it out; such a mismatch does not
enter `events[]`.

## Non-goals

The v1 contract contains no consensus sequence, sample-variant verdict,
majority-vote result, genotype, heteroplasmy estimate, haplogroup interpretation,
F/R pair object, primer/HV label, or filename-derived placement.
