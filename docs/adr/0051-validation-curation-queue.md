# ADR-0051: Separate immutable curation evidence from editable review decisions

- **Status:** Accepted
- **Date:** 2026-09-20

## Context

The validation audit now produces deterministic read, locus, and case review evidence.
Human curation is the next step before any development/holdout split or threshold study is
frozen.

The audit artifact itself must remain immutable and reproducible. Editing audit CSV files
to record reviewer decisions would invalidate their recorded hashes and mix measured
evidence with human interpretation. At the same time, generating automatic truth labels
or exclusion decisions from audit flags would exceed the evidence available in the
current corpus.

## Decision

Signal adds one external local curation-queue step,
`scripts/prepare_validation_curation.py`, consuming only one completed
`signal.validation_audit/v1` directory.

It publishes `signal.validation_curation_queue/v1` containing:

- immutable `curation-queue.csv` evidence;
- editable `curation-decisions-template.csv`;
- a hash-bound `index.json`.

The immutable queue contains exactly:

1. every mixed reference/alternate locus from `locus-audit.csv`;
2. every read with non-empty `audit_flags` from `read-audit.csv`.

No case-only review items are duplicated because case context is already represented by
the case identifier plus mixed-locus and edge-discordance counts copied into each queue
row.

Mixed loci record recurrence across distinct validation cases. Their review reasons are
descriptive only:

- `mixed_locus`;
- `recurrent_mixed_locus` when the same reference position appears in more than one
  case;
- `edge_discordance` when already present in the audit;
- `noisy_alternate` when at least one alternate observation is in a noisy region;
- `single_orientation_alternate` when alternate evidence is not observed from both
  selected orientations.

Read review reasons are the existing audit flags unchanged.

Queue ordering is deterministic workflow ordering, not a biological score:

- locus items first, ordered by recurrence count descending, then reference position and
  case ID ascending;
- read items second, ordered by case, amplicon, declared direction, and read SHA-256.

The decisions template contains the stable `review_item_id`, item type, and case ID plus
blank reviewer fields:

- `review_status`;
- `reviewer`;
- `truth_source`;
- `curation_decision`;
- `curation_notes`.

The generated template is not itself truth. Reviewer-populated decisions remain a
separate human-authored artifact until a later explicit validation/import step is
implemented.

## Consequences

- Audit evidence remains immutable and hash-verifiable.
- Human interpretation is never written back into generated audit artifacts.
- The review workload is complete for mixed loci and flagged reads without duplicating a
  second case-level queue.
- Recurrent loci are easy to review together without introducing a numeric priority score.
- No manifest truth, holdout, or threshold-fit fields are changed automatically.
- A later curation-import step can validate reviewer decisions against stable
  `review_item_id` values without changing this evidence contract.

## Non-goals

This ADR introduces no biological truth label, artifact verdict, read/sample exclusion,
development/holdout assignment, threshold, classifier, reviewer authentication, approval
workflow, or automatic manifest mutation.
