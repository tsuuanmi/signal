# Poly-C Phase Explainability

## Purpose

Summarize how much of each post-poly-C window's non-zero-reference profile mass can be
described by the complete candidate-offset curve without choosing a winning offset.

This layer consumes one immutable `signal.validation_phase_hypotheses/v1` artifact and
publishes threshold-free window and read summaries. It exists to expose reads
where profile impurity remains poorly described by every tested candidate without
declaring those reads degraded, artifactual, or biologically mixed.

## Why this is not an "unexplained" classifier

A label such as `unexplained=true` would require a threshold on impurity, shifted mass,
or residual mass. No such threshold is justified yet.

Instead the artifact exposes continuous candidate envelopes. For every source window it
retains:

- the minimum and maximum shifted-reference mass across informative candidates;
- the shifted-mass range;
- the minimum and maximum residual mass across informative candidates;
- the residual-mass range;
- the maximum fraction of candidate non-zero mass attributable to shifted-reference
  evidence;
- counts of informative and explainability-bearing candidates.

The candidate offset responsible for an extremum is intentionally not emitted. The full
candidate identities remain authoritative in the source
`signal.validation_phase_hypotheses/v1` artifact.

## Explainable non-zero fraction

For one informative candidate with positive non-zero mass:

```text
shifted_reference_mass
------------------------------------
shifted_reference_mass + residual_mass
```

The window field `candidate_explainable_nonzero_fraction_max` is the maximum value of
that quantity across the tested candidates.

This is an envelope statistic, not a selected phase. A high value means at least one
tested offset accounts for much of the candidate's non-zero mass; a low value means every
tested offset leaves a larger residual share. No candidate identity, threshold, or state
is attached to that maximum.

## Command

```bash
uv run python scripts/analyze_polyc_phase_explainability.py \
  --hypotheses-dir validation-results/research/polyc-phase-hypotheses/circular-v1 \
  --output-dir validation-results/research/polyc-phase-explainability/circular-v1
```

The output directory must not already exist.

## Output

```text
validation-results/research/polyc-phase-explainability/circular-v1/
├── index.json
├── windows.csv
└── reads.csv
```

The index is SHA-256 bound to the complete source phase-hypothesis index and preserves
the upstream poly-C phase, corpus, manifest, reference, configuration, and Signal
identities.

### `windows.csv`

One row per source phase-hypothesis window preserves:

- case/read/tract/amplicon/orientation/interrupt identity;
- exact start and end distance after the tract;
- profile and noisy-observation counts;
- window impurity and zero-reference mass;
- candidate and informative-candidate counts;
- shifted-reference and residual envelope extrema/ranges;
- maximum candidate explainable non-zero fraction.

Windows with no informative candidate retain their identity and source window metrics;
candidate-envelope fields remain empty. No fallback mass is synthesized.

### `reads.csv`

One row per:

```text
read_sha256 × tract
```

retains the stable case/read metadata plus descriptive window aggregation:

- window count;
- counts of windows with no informative or explainability-bearing candidate;
- mean and maximum window impurity;
- mean noisy fraction;
- mean/max shifted-envelope values;
- mean/max minimum-residual values;
- mean/min maximum explainable-nonzero fractions;
- mean shifted/residual candidate ranges.

These fields make reads with high impurity and persistently large residual envelopes easy
to inspect without defining a review threshold in the artifact.

## Interpretation

Useful descriptive patterns include:

- high window impurity plus high shifted-reference envelope and low minimum residual:
  compatible with structured candidate-offset explainability;
- high window impurity plus high minimum residual and low maximum explainable fraction:
  candidate offsets leave substantial profile mass unexplained;
- low impurity with no informative candidate:
  absence of candidate structure is not itself evidence of degradation;
- large candidate ranges:
  the tested offsets differ materially in how they partition shifted versus residual
  mass.

These are research interpretations only. The artifact does not assign a state to any
window or read.

## Scientific boundary

This artifact does not:

- emit a winning or best candidate offset;
- emit an `unexplained`, `degraded`, or `structured` label;
- choose impurity, residual, or explainability thresholds;
- infer an indel, genotype, or biological length heteroplasmy;
- define a phase state, classifier, breakpoint, or recovery interval;
- define confidence attenuation, evidence weighting, demixing, or a no-call rule;
- tune against holdout truth;
- modify production Rust behavior or public result schemas.

Exact recurrent-locus membership and complete candidate context are handled by [polyc-phase-recurrent-loci.md](polyc-phase-recurrent-loci.md). With that artifact, the planned descriptive ADR-0054 research surface is complete. Any production phase-state model must be a separate promotion decision.
