# Validation Curation Queue

## Purpose

Prepare a deterministic human-review workload from one completed validation audit without
turning audit evidence into truth, exclusion, holdout assignment, or production behavior.

The queue is downstream of the audit layer:

```text
signal.validation_audit/v1
            │
            ▼
signal.validation_curation_queue/v1
            ├── immutable curation-queue.csv
            └── editable curation-decisions-template.csv
```

## Command

```bash
uv run python scripts/prepare_validation_curation.py \
  --audit-dir validation-results/audit/full-20260919 \
  --output-dir validation-results/curation/full-20260919
```

The output directory must not already exist.

## Output

```text
validation-results/curation/full-20260919/
├── index.json
├── curation-queue.csv
└── curation-decisions-template.csv
```

### Immutable queue

`curation-queue.csv` contains only review items supported directly by the audit:

- every mixed reference/alternate locus;
- every read with at least one audit flag.

Case-only items are not duplicated. Each queue row carries the validation case identifier
needed to join the existing case audit when additional case context is useful.

For mixed loci the queue preserves:

- reference position;
- recurrence across distinct validation cases;
- alternate observation count;
- noisy-alternate count;
- retained-edge alternate count;
- cross-orientation alternate support;
- minimum alternate retained-edge distance;
- existing audit flags.

Its `review_reasons` field is a semicolon-separated descriptive set drawn from:

```text
mixed_locus
recurrent_mixed_locus
edge_discordance
noisy_alternate
```

These strings are review context, not truth labels.

For reads the queue preserves:

- read SHA-256;
- amplicon and declared direction;
- existing audit flags;
- callable identity;
- noisy-call fraction;
- retained fraction;
- callable columns.

The read `review_reasons` value is the existing audit flag string unchanged.

## Deterministic ordering

The queue has no numeric priority or composite score.

Mixed loci appear first and are ordered by:

1. recurrence across cases, descending;
2. reference position, ascending;
3. validation case ID, ascending.

Flagged reads follow, ordered by:

1. validation case ID;
2. amplicon ID;
3. declared direction;
4. read SHA-256.

The ordering is only a reproducible review workflow. It does not imply that an earlier
item is more biologically important.

## Human decisions

`curation-decisions-template.csv` contains the stable `review_item_id`, item type, and
case ID from the immutable queue plus blank fields:

```text
review_status
reviewer
truth_source
curation_decision
curation_notes
```

Reviewers should copy or rename this template before editing it. Editing
`curation-queue.csv` is discouraged because the queue SHA-256 recorded in
`index.json` represents generated evidence.

No reviewer vocabulary is enforced yet. Independent truth sources and curation practice
must be established before a decision-import contract is introduced.

## Provenance

`index.json` records:

- SHA-256 of the source audit index;
- source corpus/research identities propagated from the audit;
- Signal/manifest/reference/configuration identities;
- exact queue inclusion and ordering rules;
- row counts, columns, and SHA-256 for the immutable queue and blank decisions template;
- counts by review item type.

The queue contains no local AB1 path and does not read corpus, research, or log artifacts
directly. All evidence arrives through the completed audit contract.

## Current full-corpus review shape

For the current 89-case local corpus, the audit contains:

- 155 mixed loci;
- 68 reads with at least one audit flag.

Therefore the complete curation queue contains 223 immutable review items.

This count describes the current local corpus only and is not a repository contract.

## Scientific boundary

The queue answers:

> What audit-supported evidence should a human review?

It does **not** answer:

> Is this locus biologically mixed?
> Is this read unusable?
> Should this case be excluded?
> Is this case a negative or positive control?
> Which cases belong in development or holdout?
> What threshold should Signal use?

Those decisions require independent curation evidence and explicit study design.

## Next step

After human review is completed:

1. validate the populated decisions against stable `review_item_id` values;
2. reconcile only independently supported decisions into the local validation manifest;
3. freeze source-group development/holdout membership;
4. proceed to [threshold-research.md](threshold-research.md).

A future decision-import step should be implemented only when the reviewer vocabulary and
truth-source policy are concrete enough to validate.
