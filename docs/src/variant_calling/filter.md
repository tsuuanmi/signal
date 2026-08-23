# `src/variant_calling/filter.rs`

## Purpose

Applies configured report eligibility to normalized primary-sequence variant
candidates.

## Responsibilities

- Keep candidates whose normalized 1-based anchor lies in the union of configured
  inclusive regions.
- Require every SNV or inserted-base supporting call to meet the configured
  maximum-channel peak floor and strictly exceed the relative-quality threshold.
- Exempt insertion flanks and deletion flanks from supporting-signal thresholds.
- Add each removed candidate once with its normalized identity and every failed
  region/peak/relative-quality rule.

## Non-responsibilities

No extraction, normalization, vendor-quality filtering, genotype inference,
report projection, report-only label assignment, or logging.

## Key functions

- `apply(extracted, calls, quality, config) -> Result<VariantCallingResult>`:
  filters normalized candidates using domain models.
- `supporting_evidence_reasons`: selects relevant supporting mappings by kind and
  returns each failed evidence rule once.
- `call_passes`: joins one mapping to its base-call peaks and relative quality and
  evaluates the two thresholds independently.

## Invariants and errors

Region positions and normalized variant anchors are 1-based and inclusive.
Call/PLOC indexes remain 0-based. Every removed candidate creates exactly one
allele-free diagnostic, even when multiple rules fail. Missing or mismatched
call/quality mappings return `Error::Variant`. Vendor PCON does not affect
eligibility.

## Tests

Unit tests cover threshold boundaries, region endpoints, multi-base insertions,
deletion exemption, mapping errors, and exclusion accounting.

## Status

Implemented.
