# ADR-0012: Use Concise Coordinates and Direct Mapped Variant Calls

- **Status:** Accepted
- **Date:** 2026-08-24

## Context

The compact v2 contract still encoded coordinate systems in long field names and nested variant-associated calls under `evidence`. It also exposed a duplicate primary-peak position. More importantly, call records did not explicitly state their aligned biological reference position, making the relationship among normalized variant position, original ABIF call index, PLOC, and channel peaks harder to inspect for indels.

SNVs have a direct query-call/reference-base relationship. Inserted query calls have chromatogram peaks but no reference position. Deleted reference bases have positions but no trace calls or peaks. Repeat normalization may move an indel's canonical representation away from the observed alignment gap.

## Decision

Adopt `signal.analysis/v3` without compatibility aliases.

- Use context-defined concise names: biological `position`; original call `index`; ABIF `ploc`; channel peak `position`; interval `start` and `end`.
- Put associated trace calls directly in each variant's `calls` array.
- Store each call's aligned one-based biological `position` when it has one.
- Omit biological position for inserted supporting calls.
- Store deletion flanks only; never fabricate deleted-base calls, peaks, or quality.
- Preserve observed call/reference mappings when the reported indel allele is left/circular normalized.
- Remove the duplicate primary-peak position; the selected channel peak is already present under `peaks`.
- Keep variant alleles on the reference strand and call bases/peaks on the original trace strand.

Variant extraction owns call/reference mappings. Normalization owns allele representation and does not alter mappings. Report projection only joins mapped original call indexes to PLOC, peaks, and quality.

Normalization hardening for `signal.primary_difference/v2`: when no aligned left flank exists, the actual reference predecessor is derived from the event position; a true linear origin insertion/deletion right-anchors to the next reference base; circular repeats canonicalize anchor-independently; and emitted reference alleles are validated against the supplied reference. Call mappings remain unchanged throughout.

## Consequences

The JSON is shorter and the coordinate chain is explicit. Consumers must apply the documented coordinate conventions rather than infer them from suffixes. For inserted calls, absence of `position` is meaningful. For normalized repeat indels, variant position and flank positions may differ without inconsistency.

A/C/G/T peaks may occur at different sample indexes because each channel is searched independently within the shared call window; `ploc` remains the common locus anchor.

## Supersession

This ADR supersedes the v2 field names and nested `evidence` shape in ADR-0011. ADR-0011's compact-output scope and no-compatibility decision remain in force.
