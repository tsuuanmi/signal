# Phase Evidence Around Biological Errors

## Purpose

Characterize development-only post-poly-C phase evidence around biological variant-profile
missing/extra disagreements without fitting a classifier, selecting a phase offset, or
defining recovery.

The artifact consumes only already prepared development research surfaces:

```text
signal.validation_phase_interpretation_dataset/v1
        +
signal.validation_variant_phase_context/v1
        ↓
signal.validation_phase_error_characterization/v1
```

This keeps the locked holdout outside continuous feature analysis.

## Research question

The primary question is not whether an error lies near a poly-C tract. It is:

> When an exact development phase window overlaps a real reviewer-versus-Signal
> biological disagreement, how do its complete candidate curve, absolute non-zero
> evidence, candidate explainability, and ordered neighboring windows differ from
> development windows without such an overlap?

The analysis remains descriptive. An overlapping error is not proof that phase caused the
error.

## Why structured fraction is not enough

For one informative candidate:

```text
nonzero_mass = shifted_reference_mass + residual_mass

structured_fraction =
    shifted_reference_mass / nonzero_mass
```

A candidate can have a high structured fraction while the absolute non-zero mass is very
small and the window remains strongly reference-dominant.

Therefore the artifact always retains both:

- absolute zero/shifted/residual/non-zero evidence;
- the ratio describing how much candidate non-zero mass is shift-explainable.

No ratio is named confidence or probability.

## Exact biological-error annotation

Error overlap comes only from the exact window membership already published by
`signal.validation_variant_phase_context/v1`.

The join deduplicates by:

```text
difference_id × window_id
```

so a multi-base deletion that contributes multiple locus observations does not become
multiple biological errors in one window.

Each development window records counts of overlapping:

- biological disagreements;
- extra disagreements;
- missing disagreements.

The descriptive `overlap_context` value is one of:

```text
none
extra
missing
extra+missing
```

`none` means only that no exact reviewer-proxy missing/extra disagreement overlaps that
window. It is not a clean label, true negative, or proof of biological correctness.

Representation disagreements remain excluded upstream under ADR-0057.

## Candidate features

`candidates.csv` retains every candidate offset for every fit-eligible development
window and adds only deterministic derived quantities:

```text
nonzero_mass
structured_fraction
```

It also carries exact error-overlap counts and the window/read/tract context needed for
development analysis.

Candidates with zero informative positions retain absent masses and absent derived
features.

No candidate is selected or ranked.

## Window envelopes

`windows.csv` preserves each complete development window plus descriptive candidate
envelopes:

- informative and positive-nonzero candidate counts;
- maximum and mean informative positions;
- shifted-reference mass min/max/range;
- residual mass min/max/range;
- non-zero mass min/max/range;
- structured-fraction min/max/range.

Extrema are envelope statistics only. The candidate identity responsible for an extremum
is deliberately not emitted as a winner.

The source window's mean zero-reference mass, impurity, and noisy fraction remain separate
from these candidate envelopes.

## Ordered transitions

`transitions.csv` contains consecutive windows within one read/tract after sorting by
exact source start distance.

For each adjacent pair it preserves signed right-minus-left deltas for:

- zero-reference mass;
- profile impurity;
- noisy fraction;
- maximum shifted-reference mass;
- minimum residual mass;
- maximum non-zero mass;
- maximum structured fraction.

These trajectories can reveal patterns such as disturbance fading with read order, but the
artifact does not emit `affected`, `persistent`, `recovered`, or any other state.

Distance remains descriptive and never defines recovery by itself.

## Descriptive strata

`strata.csv` aggregates development windows by:

```text
overlap_context
× tract
× selected orientation
× amplicon
× sequencing run
```

and reports independent-context counts plus window-weighted descriptive means.

Window counts are correlated observations and must not be interpreted as independent
sample counts. Source-group/read counts remain visible for that reason.

## Command

First prepare the development-only interpretation dataset from the same partitioned corpus
used by the variant-phase context artifact:

```bash
uv run python scripts/prepare_phase_interpretation_dataset.py \
  --corpus-dir validation-results/corpus-phase-study-v1 \
  --hypotheses-dir validation-results/research/polyc-phase-hypotheses/phase-study-v1 \
  --output-dir validation-results/research/phase-interpretation-dataset/phase-study-v1 \
  --development-group phase-development-v1 \
  --holdout-group phase-holdout-v1
```

Then publish characterization:

```bash
uv run python scripts/analyze_phase_error_characterization.py \
  --interpretation-dir validation-results/research/phase-interpretation-dataset/phase-study-v1 \
  --context-dir validation-results/research/variant-phase-context/phase-study-v1 \
  --output-dir validation-results/research/phase-error-characterization/phase-study-v1
```

## Output

```text
validation-results/research/phase-error-characterization/<study>/
├── index.json
├── candidates.csv
├── windows.csv
├── transitions.csv
└── strata.csv
```

The index is SHA-256 bound to both prepared source artifacts and verifies that corpus,
poly-C phase, phase hypotheses, Signal version, manifest, reference, configuration, and
partition declarations agree exactly.

## Scientific boundary

This artifact does not:

- expose holdout continuous phase measurements;
- select or rank candidate offsets;
- define a phase score, confidence, probability, state, classifier, threshold, or cutoff;
- infer persistence or recovery;
- label an error as phase-caused;
- treat `overlap_context=none` as clean truth;
- infer genotype, indel length, length heteroplasmy, contamination, or artifact mechanism;
- change read/variant eligibility, sample reconciliation, unit-mass contribution, or
  no-call behavior;
- change Rust production behavior, configuration, or public schemas.

The intended next decision is whether the development evidence supports one falsifiable
feature family worth freezing for later holdout evaluation—not a production policy.
