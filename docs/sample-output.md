# Signal Sample Evidence JSON

`signal sample <sample-id> <trace.ab1>... --reference <reference.fasta>`
writes one deterministic `results/<sample-id>.sample.json` document identified as
`signal.sample_evidence/v2`. The authoritative schema is
[`schemas/sample-evidence-v2.schema.json`](schemas/sample-evidence-v2.schema.json)
and the example is
[`examples/sample-evidence-v2.example.json`](examples/sample-evidence-v2.example.json).

The sample identifier is validated naming/provenance data only. It does not
constrain read placement, orientation, overlap, or variant reconciliation.

## Reads and coverage

`reads[]` is the one registry of contributing reads. Records are sorted by
SHA-256, so CLI argument order does not change the scientific document.

Each record contains:

- `name`: UTF-8 AB1 basename for reviewer-facing provenance;
- `sha256`: stable content identity;
- `alignment`: the evidence-derived orientation, callable-base count and
  identity, unresolved-base count, gap-open count, mapped reference segments, and
  origin-wrap state.

Every `read` integer elsewhere in the document is the 0-based index into this
array. Read name, SHA-256, and orientation are intentionally not repeated in locus
or variant records.

Filename semantics are never scientific placement input. Renaming a file changes
display provenance only; duplicate detection, ordering, placement, overlap, and
variant reconciliation remain content/alignment driven.

`reference_segments` are 0-based half-open. For a segment
`{"start": S, "end": E}`, the covered 1-based biological positions are
`S + 1` through `E`, inclusive. A position outside every segment for a read is
uncovered by that read.

## Sparse locus differences

`locus_differences[]` contains only reference positions where at least one
covering read is not a canonical reference match. Dense per-position reference
records are deliberately omitted.

At a retained locus, `observations[]` contains every read that covers that locus,
including any read that agrees with the reference. This keeps explicit
reference-support quality at scientifically interesting positions without
serializing thousands of routine reference matches.

Observation states are:

- `reference`: canonical aligned query base equals the reference base;
- `alternate`: canonical aligned query base differs from the reference base;
- `unresolved`: query or reference base is not canonically comparable;
- `deletion`: the selected alignment contains a query gap at that reference base.

Called observations retain `base`, original 0-based call `index`, and
uncalibrated `relative_quality`. Deletions do not fabricate call or quality
evidence.

The compact default is therefore explicit:

- inside a read's mapped reference segments, absence of that locus from
  `locus_differences[]` means that read is a canonical reference match there;
- outside the read's mapped segments, the position is uncovered;
- at a retained differential locus, the explicit observations are authoritative.

This preserves the distinction between reference support and missing coverage
without emitting routine reference loci one by one.

Inserted query columns have no reference-coordinate locus. They are represented
through normalized variant evidence rather than fabricated locus observations.

## Variants

`variants[]` aggregates normalized canonical read-level observations by
`(position, reference, alternate, kind)` before configured eligibility removes
them from the single-read report.

Each support record contains:

- `read`: index into top-level `reads[]`;
- `eligible`: whether the read-level candidate satisfies configured reporting
  eligibility;
- `exclusion_reasons`: exact failed configured rules when ineligible;
- `calls[]`: concise original-call pointers.

A call pointer contains its role, original 0-based call `index`, optional
1-based aligned reference `position`, and 0-based ABIF `ploc`. This permits a
reviewer to drill into the corresponding per-read analysis without duplicating
chromatogram payloads.

An eligible support has an empty exclusion list. An ineligible support retains one
or more reasons such as `outside_configured_region`,
`peak_below_minimum`, or
`relative_quality_not_above_threshold`. A normalized variant observed by a read
remains sample evidence even when that read is not eligible for single-read
reporting.

## Contract boundary

v2 is intentionally sparse and difference-focused. It does not serialize
per-base quality for loci where every covering read agrees with the reference.
The scientific pipeline still processes each read independently before sample
aggregation; future interpretation that needs additional focused evidence should
derive it from those read observations rather than reintroducing a dense
whole-coverage table.

The current implementation emits v2 only. There is no v1 alias or compatibility
output.

## Non-goals

The v2 contract contains no consensus sequence, sample-level adjudicated variant
verdict, majority-vote result, genotype, heteroplasmy estimate, haplogroup
interpretation, F/R pair object, primer/HV label, or filename-derived placement.
