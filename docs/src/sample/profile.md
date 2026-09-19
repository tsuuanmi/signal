# `src/sample/profile.rs`

## Purpose

Resolves one call's basecall-independent `EvidenceProfile` from an immutable
`ReadObservation` and projects it into the selected reference orientation.

## Responsibilities

- Look up the authoritative `LocusEvidence` by original call index.
- Require the stored locus index to match the requested call index.
- Preserve a valid absent profile as `None`.
- Keep forward-read A/C/G/T weights unchanged.
- Complement reverse-read profile channels as A↔T and C↔G.
- Return typed sample errors for missing or misindexed locus evidence.

## Non-responsibilities

No basecalling, profile construction, weighting, normalization, consensus,
variant eligibility, gap evidence synthesis, or public JSON projection.

## Invariants

The helper never reconstructs profile evidence from primary/ambiguity calls,
peak thresholds, relative quality, or the reference. Reverse projection creates
a value for sample reconciliation without mutating the source read evidence.

## Status

Implemented.
