# Poly-C Opposite-Orientation Controls

## Purpose

Measure whether a read that has already crossed an rCRS HV1/HV2 poly-C tract differs
from overlapping evidence that reaches the same locus from the opposite selected
orientation before crossing that tract.

This is a descriptive internal-control layer for ADR-0052/ADR-0054. It consumes the
completed `signal.validation_corpus/v1` directly because the phase-hypothesis artifacts
intentionally drop case/read acquisition provenance that is required to construct valid
same-case controls.

## Matching boundary

A control group is identified by:

```text
validation_case_id × tract_id × position_1based × post_orientation
```

The validation case is the sample execution boundary. `source_group_id` and
`specimen_group_id` are preserved for provenance but are not used as substitutes for
sample identity.

For v1, both roles require explicit complete-tract coverage so before/after state can be
proven from call order:

- `post_tract`: selected orientation equals `post_orientation` and the locus occurs
  after the complete tract call span;
- `pre_tract_opposite_control`: selected orientation is the opposite orientation and
  the same locus occurs before that tract's complete call span.

`declared_direction` remains acquisition metadata only. It never determines role.

This conservative rule deliberately excludes shorter opposite-orientation reads whose
relationship to the tract cannot yet be proven from complete tract coverage. A future
research extension may formalize those non-crossing controls separately.

## N-read model

The artifact does not choose one forward/reverse pair.

For example, if one matched locus contains two eligible post-tract reads and three
eligible opposite-orientation controls, the artifact retains five observation rows.
It does not create six pairwise comparisons.

This avoids pseudo-replication and remains compatible with:

- technical resequencing;
- independent PCR replicates;
- multiple overlapping amplicons;
- more than one read per selected orientation.

PCR replicate, sequencing run, instrument, amplicon, declared direction, and artifact
tags are retained per observation for later stratification. None is a hidden eligibility
filter.

## Command

```bash
uv run python scripts/analyze_polyc_orientation_controls.py \
  --corpus-dir validation-results/corpus \
  --output-dir validation-results/research/polyc-orientation-controls/baseline
```

The output directory must not already exist.

## Output

```text
validation-results/research/polyc-orientation-controls/baseline/
├── index.json
├── observations.csv
└── loci.csv
```

The index is SHA-256 bound to the completed corpus index and records the Signal,
manifest, reference, and configuration identities.

### `observations.csv`

One row per eligible read retained inside a matched control group. The row preserves:

- control/case/source/specimen identity;
- tract, locus, reference base, and post orientation;
- role and selected read orientation;
- read SHA-256 and PCR/run/instrument/amplicon metadata;
- declared direction and artifact tags as metadata only;
- call-order and circular-rCRS distance from the tract;
- state/base/quality/noisy-region evidence;
- normalized reference-oriented A/C/G/T profile when present;
- profile impurity and reference-base mass when a profile exists.

Missing profiles remain missing. No uniform, reference-guided, or role-based profile
fallback is introduced.

### `loci.csv`

One row per matched control group summarizes the two roles without pair expansion:

- read count and profile-bearing read count;
- noisy-observation count;
- mean profile impurity;
- mean reference-base mass;
- arithmetic mean A/C/G/T profile for each role;
- Total Variation distance between the two role mean profiles when both means exist.

The Total Variation value is descriptive:

```text
0.5 × Σ |mean_post_i - mean_control_i|
```

It is not a pass/fail criterion, classifier, confidence multiplier, or artifact score.

## Interpretation

The strongest directional-control pattern would be:

- a post-tract role with increased impurity or changed profile geometry;
- an opposite-orientation pre-tract role at the same case/locus that remains cleaner;
- recurrence of that pattern across independent loci/reads/replicates.

The artifact itself does not decide whether that pattern is present strongly enough to
support production attenuation. Same-PCR, independent-PCR, and cross-amplicon comparisons
must remain distinguishable when the real corpus is analyzed.

A true biological SNV can reduce reference-base mass in both roles. Therefore reference
mass alone is not interpreted as control quality; complete A/C/G/T profiles and their
descriptive distance are retained.

## Scientific boundary

This artifact does not:

- infer biological genotype or length heteroplasmy;
- label either role as artifact;
- select a best post/control read pair;
- count pairwise read combinations as independent evidence;
- use declared direction as placement/orientation truth;
- define a phase score, phase state, breakpoint, or recovery threshold;
- define confidence attenuation, evidence weighting, or a no-call rule;
- modify production Rust behavior or public result schemas.

## Privacy

The artifact contains sample/case identifiers, trace hashes, acquisition metadata, and
locus-level biological signal evidence. It remains ignored local validation data under
the same approval, retention, and redistribution policy as the source corpus.
