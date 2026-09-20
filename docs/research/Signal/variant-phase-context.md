# Variant Disagreement Phase Context

## Purpose

Join biological variant-profile disagreements that remain after ADR-0057 representation
equivalence handling to the exact read-local post-poly-C phase evidence that overlaps the
normalized event reference footprint.

The artifact answers an explanatory question: for a real reviewer-versus-Signal missing
or extra biological disagreement, which available post-tract read observations and exact
phase windows overlap the event, and what complete candidate-offset evidence was present?

It does not claim that phase caused the disagreement.

## Inputs

The analysis consumes four completed, hash-bound validation artifacts:

```text
signal.validation_variant_profile_evaluation/v2
signal.validation_corpus/v1
signal.validation_polyc_phase/v1
signal.validation_phase_hypotheses/v1
```

All reference, configuration, corpus, manifest, and Signal identities must agree.
Representation disagreements are excluded because ADR-0057 already treats them as the
same resolved haplotype rather than biological false positives or false negatives.

## Anti-leakage boundary

Detailed disagreement, observation, window, and candidate tables are emitted only for
cases in the declared development partition with `include_in_threshold_fit=true`.
Holdout, excluded, unassigned, and fit-excluded development cases contribute only
aggregate readiness counts. Continuous holdout phase/error context therefore remains
unavailable during rule development.

## Event footprint

Evaluator-v2 source events use `KIND:position:REFERENCE>ALTERNATE`. The explanatory
footprint is the normalized reference-allele span. Insertions retain their normalized
anchor as the one-position footprint and also expose `insertion_boundary_after_1based`.
This is a context join boundary, not a claim that every anchored reference base changed.

## Exact phase membership

Window context is never assigned by interval-only containment. The implementation reuses
the same validated phase/hypothesis source pair and exact reconstructed profile-bearing
window membership used by recurrent-locus phase research.

A disagreement may therefore have no post-tract observation, post-tract observations but
no complete window, or observations that are exact members of one or more windows.
Absence is preserved; it is not interpreted as clean, recovered, or unaffected.

## Output

```text
validation-results/research/variant-phase-context/<study>/
├── index.json
├── differences.csv
├── observations.csv
├── windows.csv
├── candidates.csv
└── readiness.csv
```

`differences.csv` contains fit-eligible development missing/extra disagreements only.
`observations.csv` joins their footprints to exact available post-tract observations and
retains acquisition metadata, selected orientation, tract context, signal state, profile,
and noisy-region evidence. `windows.csv` contains exact containing windows.
`candidates.csv` retains every source candidate offset plus exact locus contribution.
No winning offset, phase state, score, confidence, artifact label, or threshold is emitted.

`readiness.csv` exposes aggregate counts by study partition and difference type without
per-case holdout disagreement identity or continuous holdout phase features.

## Command

```bash
uv run python scripts/analyze_variant_phase_context.py \
  --evaluation-dir validation-results/variant-profile/baseline \
  --corpus-dir validation-results/corpus \
  --phase-dir validation-results/research/polyc-phase/baseline \
  --hypotheses-dir validation-results/research/polyc-phase-hypotheses/baseline \
  --output-dir validation-results/research/variant-phase-context/baseline \
  --development-group development \
  --holdout-group holdout \
  --unassigned-group unassigned
```

## Intended research use

This artifact supports questions such as whether residual extra variants are enriched in
post-tract evidence, whether their exact windows are shift-explainable or residual-heavy,
and whether missing reviewer variants reflect distorted read evidence versus a later
sample-reconciliation failure. Multiple orientations, amplicons, PCR replicates, runs,
and instruments remain explicit context rather than hidden eligibility rules.

These are attribution and falsification questions, not causal labels.

## Scientific boundary

This artifact does not call a phase state, choose an offset, infer biological mechanism,
declare phase to be the cause of an FP/FN, attenuate evidence, change variant eligibility
or sample reconciliation, expose holdout continuous context, or modify Rust production
behavior, configuration, or public schemas.

Future interpretation remains governed by `polyc-phase-interpretation-study.md` and
`docs/validation/polyc-phase-promotion.md`.
