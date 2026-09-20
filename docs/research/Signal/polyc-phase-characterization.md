# Poly-C Phase-Hypothesis Characterization

## Purpose

Characterize the complete candidate-offset curves produced under ADR-0054 before any
phase detector, recovery model, or production policy is proposed.

This layer consumes one immutable
`signal.validation_phase_hypotheses/v1` artifact and publishes descriptive persistence,
distance-trajectory, and interrupt-stratified summaries. It does not reopen AB1 files,
recompute phase hypotheses, or choose a preferred offset.

## Research questions covered

This artifact addresses three questions from the phase-hypothesis research plan:

1. how candidate curves differ by the read-local observed interrupt base;
2. whether evidence for the same candidate offset is stable between adjacent downstream
   windows of one read;
3. how candidate mass and unexplained residual change with distance after the tract.

The observed interrupt base is evidence from one read. It is not interpreted as the
sample genotype at T310 or T16189.

## Command

```bash
uv run python scripts/analyze_polyc_phase_characterization.py \
  --hypotheses-dir validation-results/research/polyc-phase-hypotheses/full-20260919 \
  --output-dir validation-results/research/polyc-phase-characterization/full-20260919
```

The output directory must not already exist.

## Output

```text
validation-results/research/polyc-phase-characterization/full-20260919/
├── index.json
├── persistence.csv
├── trajectory.csv
└── strata.csv
```

The index is hash-bound to the complete source phase-hypothesis index and preserves the
upstream corpus, manifest, reference, configuration, and Signal identities.

### `persistence.csv`

For every pair of consecutive source windows from one read/tract and every declared
candidate offset, preserve:

- both window identities and start distances;
- informative-position counts on both sides;
- zero-reference, shifted-reference, and residual masses on both sides;
- the absolute change in each mass component.

"Consecutive" means consecutive in the source window ordering after sorting by read-order
start distance. No numeric persistence cutoff is applied.

This table intentionally does **not** emit a boolean such as `persistent=true`. Stability
remains visible as measured changes in the underlying candidate evidence.

### `trajectory.csv`

Aggregate every candidate offset by:

```text
tract × amplicon × orientation × observed interrupt base
× exact source-window start distance × candidate offset
```

The table preserves window count, informative-window count, mean informative positions,
mean zero/shifted/residual mass, mean window profile impurity, and mean noisy-window
fraction.

Distance is kept at the exact source-window start distance. This research layer introduces
no bins, recovery interval, or recovery threshold.

### `strata.csv`

Aggregate the same descriptive metrics by:

```text
tract × amplicon × orientation × observed interrupt base × candidate offset
```

This makes T-versus-C and other observed interrupt strata inspectable without assigning a
genotype or selecting a winning candidate.

## Why every candidate remains explicit

A summary such as "best shift" would prematurely turn an explanatory curve into a
classifier. This layer instead carries every declared candidate offset through all three
outputs.

That keeps several possibilities distinguishable:

- one offset remains elevated across nearby windows;
- multiple offsets remain similarly plausible;
- shifted mass fades with distance while residual remains high;
- both shifted and residual mass fall;
- impurity stays high without one candidate becoming structurally explanatory.

Those patterns can later motivate a detector, but they are not detector states here.

## Remaining ADR-0054 analyses

This characterization does not itself answer whether recurrent loci 253, 297, 302,
16194, and 16197 occur inside windows with coherent shifted-reference support.

Opposite-orientation evidence is handled separately by [polyc-orientation-controls.md](polyc-orientation-controls.md), which joins same-case locus context from the completed corpus rather than trying to reconstruct lost provenance from phase-hypothesis summaries. Parameter sensitivity is handled by [polyc-phase-sensitivity.md](polyc-phase-sensitivity.md) using the same candidate engine and candidate-wise aggregation. Per-window/read residual explainability is handled by [polyc-phase-explainability.md](polyc-phase-explainability.md) without a winning-candidate rule or review threshold. Recurrent-locus joins remain the outstanding descriptive context analysis.

## Scientific boundary

This artifact does not:

- select a winning offset or phase;
- infer an insertion/deletion length or biological length heteroplasmy;
- interpret the observed interrupt base as genotype;
- define a phase-state classifier or score;
- define a breakpoint or recovery distance;
- define evidence attenuation, confidence weighting, or a no-call rule;
- rewrite calls, profiles, alignment, or variants;
- change production Rust behavior or public result schemas.
