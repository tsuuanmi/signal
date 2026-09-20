# Poly-C Phase Parameter Sensitivity

## Purpose

Test whether the descriptive post-poly-C candidate-offset patterns observed under
ADR-0054 are stable to reasonable research choices for downstream window size, stride,
and maximum tested offset.

This layer consumes one immutable `signal.validation_polyc_phase/v1` artifact and calls
the same candidate engine used by `signal.validation_phase_hypotheses/v1`. It does not
write one phase-hypothesis artifact per parameter set and it does not introduce a second
candidate implementation.

## Default parameter grid

The default study is a full factorial grid:

```text
window size:  15, 25, 35 profile-bearing observations
window step:  5, 10 profile-bearing observations
max offset:   3, 5, 7 reference positions in read order
```

This yields 18 parameter sets. Values remain explicit research inputs and can be
overridden from the CLI.

The existing phase-hypothesis defaults `25 / 5 / 5` are included in the default grid,
but the sensitivity artifact does not designate a winner or treat that set as ground
truth.

## Command

```bash
uv run python scripts/analyze_polyc_phase_sensitivity.py \
  --phase-dir validation-results/research/polyc-phase/circular-v1 \
  --output-dir validation-results/research/polyc-phase-sensitivity/circular-v1
```

Optional explicit grid values:

```text
--window-sizes 15 25 35
--window-steps 5 10
--max-offsets 3 5 7
```

Duplicate, zero, negative, or empty parameter dimensions are rejected.

## Output

```text
validation-results/research/polyc-phase-sensitivity/circular-v1/
├── index.json
├── parameter_sets.csv
└── strata.csv
```

The artifact is hash-bound to the source poly-C phase index and preserves the upstream
corpus, manifest, reference, configuration, and Signal identities.

### `parameter_sets.csv`

One row per full-factorial parameter set records:

- deterministic parameter-set ID;
- window size;
- window stride;
- maximum tested offset;
- complete non-zero candidate offset list;
- generated window count;
- generated candidate-row count.

The raw generated windows and candidates are not duplicated on disk. They are transient
inputs to the same characterization aggregation used by the single-configuration
research path.

### `strata.csv`

For every parameter set and every:

```text
tract × amplicon × orientation × observed interrupt base × candidate offset
```

retain the same descriptive fields used by
`signal.validation_phase_characterization/v1`:

- window count;
- informative-window count;
- mean informative positions;
- mean zero-reference mass;
- mean shifted-reference mass;
- mean residual mass;
- mean window impurity;
- mean noisy-window fraction.

Offsets that do not exist in a parameter set are absent because that set never evaluated
them. No common-offset interpolation or synthetic fill is introduced.

## Questions this artifact can answer

The study is intended to test whether observations such as these remain qualitatively
stable across the explicit parameter grid:

- C-interrupt strata have higher post-tract impurity than T-interrupt strata;
- one-base candidate offsets retain elevated shifted-reference mass;
- residual mass remains lower than shifted-reference mass in structured windows;
- direction/tract patterns are not created solely by one window size or stride.

Those conclusions must be inspected from the candidate-wise strata. The artifact does
not compute a robustness score, rank parameter sets, or select a preferred configuration.

## Scientific boundary

This artifact does not:

- select a best parameter set;
- select a winning candidate offset;
- infer an indel, genotype, or biological length heteroplasmy;
- define a phase state, classifier, breakpoint, or recovery interval;
- define a confidence weight, evidence attenuation, demixing, or no-call rule;
- tune against holdout truth;
- modify production Rust behavior or public result schemas.

Only after parameter sensitivity and unexplained high-impurity read analysis should a
separate promotion discussion consider any production phase-state model.
