# Reviewer Variant-Profile Baseline Evaluation

## Purpose

Establish a deterministic local baseline for the end-to-end scientific objective:

> Given all usable AB1 traces for one sample, does Signal recover the reviewer-supported
> sample variant profile without extra variants or missing variants?

This evaluator is validation tooling only. It does not change Rust production behavior,
phase measurement, variant extraction, eligibility, sample aggregation, configuration, or
public result schemas.

## Inputs

The baseline consumes:

1. one local ignored `signal.reviewer_variant_ground_truth/v1` artifact;
2. current `signal.sample_evidence/v8` sample outputs under `results/<sample-id>/<sample-id>.json`;
3. the exact reference FASTA used by those sample outputs.

Every evaluated sample result is SHA-256 bound into `samples.csv`, and every result must
declare the same `configuration_sha256`. Mixed configurations fail rather than being
silently pooled. The output index records that shared configuration identity plus the
reference and reviewer-artifact identities.

The reviewer artifact is proxy ground truth, not independent biological truth.

The two reviewer identities have distinct roles:

```text
sample_id            production sample/result identity, e.g. LN_26_AB0442
validation_case_id   validation-corpus join identity, e.g. AB0442
```

The evaluator locates and validates the Signal result strictly by `sample_id`. It does not
guess paths from `validation_case_id`, scan filenames, or retain a legacy fallback.
`validation_case_id` remains in evaluation rows so later phase/corpus joins are explicit.


## Reviewer notation

The current Sequencher source notation is interpreted only in the evaluator:

```text
310.1C   insertion C after reference position 310
310DEL   deletion of the reference base at position 310
310A     SNV at position 310 from the reference base to A
```

Additional rules:

- multiple `P.nBASE` tokens at one position form one insertion in ascending `n`;
- consecutive `PDEL` positions form one deletion event;
- IUPAC SNV symbols preserve the allowed alternate-base set;
- the original `Variants (Sequencher)` string remains immutable in the source artifact.

The evaluator must not rewrite the reviewer artifact to match Signal representation.

## Signal baseline profile

The current baseline sample profile contains every normalized sample variant with:

```text
support_topology.eligible_reads > 0
```

This is deliberately based on the existing v8 evidence contract. The evaluator does not
invent a new consensus vote or phase-aware policy.

## Matching

Matching is representation-aware but deliberately conservative.

### Exact identity

Exact one-to-one events match by:

```text
(position, reference, alternate, kind)
```

For IUPAC reviewer SNVs, any canonical alternate allowed by the reviewer symbol may match.

### Single-event representation equivalence

An unmatched reviewer event may match one unmatched Signal event when applying each event
to the same reference produces exactly the same resulting sequence. The pair is retained
as a `representation` disagreement rather than an FP/FN.

### Multi-event haplotype equivalence

After exact and single-event matching, v2 may compare contiguous unmatched event groups.
A reviewer group is eligible only when every event has one unambiguous alternate and the
events can be applied without overlapping reference spans. A reviewer group and a Signal
group are representation-equivalent only when applying each complete group to the same
reference produces exactly the same resulting sequence.

This allows, for example, a reviewer SNV plus repeat-end deletion to match one canonical
right-aligned Signal deletion when both descriptions encode the same haplotype.

The evaluator does **not** use locus lists, repeat annotations, poly-C coordinates, or a
maximum distance threshold to create such groups. A candidate group must be minimal: if a
proper subgroup is already sequence-equivalent, the larger grouping is rejected. If an
event participates in more than one competing minimal equivalence group, none of those
ambiguous groups is collapsed.

### Why grouping is required

In repeat sequence, one biological sequence difference can admit different event
decompositions. Correctness therefore cannot be defined by raw position equality alone.
The evaluator first preserves source events, then evaluates canonical comparison groups.

The evaluator does not ignore unmatched variants merely because they are close to a repeat
or poly-C tract.

## Metrics

The v2 baseline reports both source-event counts and canonical comparison-group counts:

- reviewer source events;
- Signal source events;
- canonical reviewer groups;
- canonical Signal groups;
- matched groups;
- representation groups;
- collapsed reviewer/Signal source events;
- extra Signal groups: proxy false positives;
- missing reviewer groups: proxy false negatives;
- exact sample profiles;
- proxy precision;
- proxy recall.

A representation group counts once on each side for FP/FN accounting regardless of whether
its source representation was 1↔1, N↔1, 1↔M, or N↔M. A sample with any representation
group is not an exact representation match.

A variant-only reviewer profile does not define a complete negative-locus denominator.
Therefore v2 deliberately does **not** fabricate true-negative counts or specificity.

True negatives/specificity require a separately frozen reviewed callable/reference domain.

## Phase independence

The baseline evaluator contains no hard-coded:

- poly-C positions;
- recurrent loci;
- HV1/HV2 special cases;
- post-tract distance rules;
- phase thresholds.

Its job is to freeze the current sample-level outcome before phase-aware behavior changes.

Later phase studies may join the baseline differences to independently computed read/tract
phase context for stratified analysis, but that join must not change what counts as a
reviewer match.

## Non-regression objective

The current caller is already useful in unaffected/pre-poly-C evidence. Future phase-aware
changes therefore compare against this frozen baseline.

The desired direction is:

```text
unaffected / pre-tract:
    no material regression

phase-affected / post-tract:
    fewer false positives
    no increase in false negatives; ideally fewer
```

An improvement in false positives does not justify an unacceptable increase in false
negatives, and vice versa.

## Local workflow

Create the local reviewer proxy artifact:

```bash
uv run python scripts/extract_reviewer_variant_ground_truth.py \
  "path/to/reviewer-comparison.tsv"
```

The default output is:

```text
data/validation/ground-truth/reviewer-variant-ground-truth.json
```

Evaluate the current Signal batch outputs:

```bash
uv run python scripts/evaluate_variant_profiles.py
```

The default no-overwrite v2 output is:

```text
validation-results/variant-profile/baseline/
├── index.json
├── samples.csv
└── differences.csv
```

Real artifacts remain ignored local validation data.

## Promotion use

This baseline is a comparator, not a promotion by itself.

Before a future phase-aware calling policy is accepted:

1. freeze this baseline against the chosen reviewer/independent truth artifact;
2. develop phase interpretation without using absolute recurrent-locus identity as a
   classifier input;
3. freeze the phase-aware rule before locked holdout inspection;
4. compare baseline and phase-aware final sample profiles;
5. require non-regression on unaffected evidence;
6. require an acceptable joint FP/FN tradeoff on phase-affected evidence;
7. review representation disagreements separately from biological disagreements.

The final decision remains based on sample variant-profile correctness, not phase-state
accuracy alone.
