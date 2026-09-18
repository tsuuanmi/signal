# ADR-0016: Derive Read Coverage and Orientation From Alignment Evidence

- **Status:** Accepted for research
- **Date:** 2026-09-18

## Context

A sample may contain files named or described as HV1F, HV1R, HV2F, HV3R, or
other assay-specific labels. Those labels are useful provenance, but they are
not chromatogram evidence.

Pre-assigning an expected region or orientation can make placement circular:
the system first assumes where a read belongs and then "confirms" it by only
searching that region.

Signal's current mtDNA reference is small enough to align against the complete
circular reference without an assay-region shortcut.

## Decision

For the default mtDNA sample workflow, a read's mapped reference span and
orientation shall be derived from the authoritative alignment result.

Filename, amplicon label, primer label, declared direction, or other manifest
metadata shall not constrain candidate placement or orientation by default.

Optional assay metadata may be compared **after** mapping for provenance or QC.
A disagreement is a metadata/QC condition, not a reason to rewrite or relocate
the scientific alignment.

The same AB1 analyzed with the same reference, configuration, and Signal
version shall produce the same read placement regardless of filename or
amplicon/direction labels.

## Consequences

Reads can be supplied without knowing which region they cover. Cross-amplicon
overlap emerges naturally from mapped coordinates.

Mislabeled files remain detectable instead of being forced into the expected
region.

If a future large-reference workflow introduces metadata-assisted candidate
search for performance, that behavior must be explicit, optional, separately
versioned, and must retain an unbiased fallback/validation path.


## Implementation rationale from Tracy

Tracy demonstrates two ways to achieve evidence-driven placement.

For a short FASTA, it uses semi-global profile alignment with free reference
flanks. The query trace must align, while unused reference prefix/suffix does
not penalize the score. The traceback therefore determines the covered reference
interval.

For a large indexed genome, Tracy uses exact k-mer anchoring only to propose a
candidate local slice, then performs profile alignment inside that slice.

The common invariant is:

~~~text
read evidence
    ->
placement algorithm
    ->
mapped region
~~~

not:

~~~text
declared assay region
    ->
restricted search
    ->
mapped region
~~~

## Signal implementation consequence

Current Signal already has the required short-reference primitive.

`gotoh::align()` returns a traceback-derived `start_reference` and
`end_reference`. `align_best()` independently evaluates forward and
reverse-complement query orientations and projects the selected placement into
one or two `reference_segments` for circular references.

Future sample code should consume those fields directly.

This ADR therefore does not require a new region classifier. It requires that
sample-level APIs preserve and trust the existing evidence-derived placement and
keep optional assay labels downstream.
