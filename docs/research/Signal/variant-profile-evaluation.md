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
2. current `signal.sample_evidence/v8` sample outputs under `results/<case>/<case>.json`;
3. the exact reference FASTA used by those sample outputs.

Every evaluated sample result is SHA-256 bound into `samples.csv`, and every result must
declare the same `configuration_sha256`. Mixed configurations fail rather than being
silently pooled. The output index records that shared configuration identity plus the
reference and reviewer-artifact identities.

The reviewer artifact is proxy ground truth, not independent biological truth.

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

Matching occurs in two steps.

### Exact identity

Exact variants match by:

```text
(position, reference, alternate, kind)
```

For IUPAC reviewer SNVs, any canonical alternate allowed by the reviewer symbol may match.

### Representation equivalence

An unmatched single indel may match an unmatched reviewer indel when applying each event to
the same reference produces the same resulting sequence. Such a match counts as the same
sequence difference but is recorded separately as a `representation` disagreement.

This is important in repeats/homopolymers where equivalent indels can have different
anchors.

The evaluator does not ignore unmatched variants merely because they are close to a repeat
or poly-C tract.

## Metrics

The baseline reports reviewer-proxy counts:

- matched variants;
- extra Signal variants: proxy false positives;
- missing reviewer variants: proxy false negatives;
- representation disagreements;
- exact sample profiles;
- proxy precision;
- proxy recall.

A variant-only reviewer profile does not define a complete negative-locus denominator.
Therefore v1 deliberately does **not** fabricate true-negative counts or specificity.

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
    fewer false negatives
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

The default no-overwrite output is:

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
