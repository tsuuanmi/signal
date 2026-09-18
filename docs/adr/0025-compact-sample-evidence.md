# ADR-0025: Factor sample evidence into a read registry and sparse differences

- **Status:** Accepted
- **Date:** 2026-09-19

## Context

ADR-0024 introduced the first multi-read evidence contract. Its dense locus model
proved scientifically explicit but operationally noisy: every covered reference
position repeated read name, SHA-256, orientation, state, call index, and relative
quality even when all reads simply matched the reference.

Review of the LN_26_AB0444 sample output made the imbalance concrete. The document
contained 1,027 locus records and 1,814 locus observations; 1,793 observations were
reference matches, while only 12 loci contained any non-reference state. The
resulting sample JSON was roughly 703 KB even though the scientifically interesting
difference set was small.

Read identity, orientation, and mapped reference segments are already known once
the independent read observations have been placed. Repeating those facts at every
locus does not add evidence. At the same time, simply deleting all reference
observations would lose useful reference-support quality at positions where another
read differs.

The output contract therefore needs to factor shared read metadata once, make
coverage semantics explicit, and retain detailed locus evidence only where a
difference exists.

## Decision

Signal replaces `signal.sample_evidence/v1` with `signal.sample_evidence/v2`. The
current implementation emits v2 only; no v1 compatibility result or alias is
retained.

### Read registry

`reads[]` is the single deterministic registry of contributing reads and is sorted
by input SHA-256. Each entry owns reviewer-facing basename provenance, stable
SHA-256 identity, derived orientation, alignment summary, and mapped reference
segments.

All locus and variant evidence refers to a read by its 0-based index in this
registry. Read name, SHA-256, and orientation are not duplicated downstream.

### Sparse differential loci

The dense `loci[]` table is replaced by `locus_differences[]`.

A locus is retained only when at least one covering read is alternate, unresolved,
or deletion. Once a locus is retained, every read covering that position is
included, including canonical reference observations with original call index and
relative quality.

Aggregation uses two passes:

1. discover reference positions with at least one non-reference state;
2. collect all covering-read observations only for those positions.

Mapped reference segments define coverage. For a given read:

- a 1-based position inside its mapped segments but absent from `locus_differences[]`
  is a canonical reference match;
- a position outside its mapped segments is uncovered;
- a retained differential locus uses its explicit observations.

This preserves the distinction between reference support and missing coverage
without materializing routine all-reference positions.

### Normalized variants

`variants[]` remains the normalized variant layer. Per-read support keeps
configured eligibility, exclusion reasons, and original-call mappings, but the read
is represented only by the registry index.

Read-level filtering changes eligibility, not whether the normalized observation
exists in sample evidence.

### Versioning

The shape change is incompatible with v1, so it is a new schema version rather
than a mutation of the accepted v1 schema. The v1 schema/example and implementation
are removed instead of maintained as a compatibility layer.

## Consequences

- Sample output size scales primarily with reads plus differences rather than with
  every covered reference base.
- Reviewer-facing filenames remain easy to find without being repeated or used as
  scientific keys.
- Reference-support call quality remains explicit at loci where another read
  differs.
- Routine per-base reference quality is intentionally absent from the public sample
  document. Full one-read evidence still exists upstream before sample aggregation;
  future interpretation needing additional focused evidence should derive it there
  rather than restore a dense whole-coverage table.
- Variant support becomes more concise because read identity and orientation are
  factored to the read registry.
- The internal sample implementation is split into validation/read ordering,
  differential-locus aggregation, and normalized-variant aggregation modules.

## Non-goals

This decision does not add consensus, majority voting, conflict adjudication,
genotype, heteroplasmy estimation, haplogroup inference, metadata-driven
placement, or canonical F/R pairing.
