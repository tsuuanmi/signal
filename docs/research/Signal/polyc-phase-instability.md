# Poly-C Phase-Instability Research

## Purpose

Measure whether mtDNA Sanger reads lose phase after crossing the two canonical rCRS
control-region poly-C tracts, without changing production calling or introducing a phase
score.

This work implements the descriptive research step behind
[ADR-0052](../../adr/0052-post-polyc-directional-confidence.md). ADR-0052 remains the
production-facing invariant; this document defines only the validation measurement
artifact used to test the mechanism.

## rCRS tracts

The research is explicitly rCRS-bound:

| Tract | rCRS positions | Reference sequence | Interrupt |
|---|---:|---|---:|
| `HV2_C` | 303–315 | `CCCCCCCTCCCCC` | T310 |
| `HV1_C` | 16184–16193 | `CCCCCTCCCC` | T16189 |

Before assigning either tract ID, the analyzer reconstructs the reference bases observed
in the validation measurements and requires the complete represented tract to match this
rCRS sequence. A partially represented tract is rejected; a tract absent from the corpus
is skipped.

## Directional rule

Poly-C context is a **read-path property**, not a global locus mask.

A read contributes to this research for a tract only when its selected placed span covers
the complete tract. For every observation on such a read:

- `before` means the observation occurs before the tract in sequencing order;
- `inside` means the observation lies inside the tract;
- `after` means the read has already crossed the tract before reaching the observation.

Therefore the same genomic locus can have different path regions on opposite read
orientations.

The signed `read_order_distance_from_tract` is:

- negative before the tract;
- zero inside the tract;
- positive after the tract.

When source call indexes exist at the relevant tract boundary,
`call_distance_from_tract` records the equivalent signed distance in call order.

No hard-coded post-tract exclusion or recovery distance is used.

## Command

```bash
uv run python scripts/analyze_polyc_phase.py \
  --corpus-dir validation-results/full-20260919 \
  --output-dir validation-results/research/polyc-phase/full-20260919
```

The output directory must not already exist.

## Output

```text
validation-results/research/polyc-phase/full-20260919/
├── index.json
├── observations.csv
└── summary.csv
```

### `observations.csv`

One row per covered locus/read/tract combination for a read that spans the complete tract.

The row preserves:

- validation case/source/specimen identifiers;
- read SHA-256 and assay metadata;
- selected orientation and placed read span;
- tract identity and coordinates;
- before/inside/after path region;
- signed genomic and, when available, call-order tract distance;
- locus reference/state/base/quality/noisy context;
- normalized reference-oriented A/C/G/T profile and simple `1 - max(profile)` impurity;
- the reference base immediately before and after the locus in **sequencing order**;
- profile mass assigned to the previous/current/next reference bases;
- read-local evidence at T310 or T16189: state/base/call index/profile/noisy context.

The interrupt fields are read observations, not sample genotype truth.

### Why previous/next base mass is retained

A one-base sequencing phase shadow can project signal from a neighboring reference base
into the current event. The dataset therefore keeps the raw previous/current/next
reference-base profile masses.

It does **not** combine them into a `phase_shadow_score`. Whether one-sided neighbor mass,
multi-base lag structure, or another representation best identifies dephasing must be
decided from the real corpus.

### `summary.csv`

Descriptive summaries group observations by:

```text
tract × amplicon × selected orientation × interrupt observed base × path region
```

For each group the table reports:

- observation/profile/noisy counts;
- mean, empirical p50, and empirical p90 profile impurity;
- mean, empirical p50, and empirical p90 previous-reference-base mass;
- the same summaries for next-reference-base mass.

Percentiles use the existing exact nearest-rank implementation.

These summaries are exploratory. They are not thresholds or confidence weights.

## Two-pass implementation

The analyzer deliberately does not retain the full validation observation dataset in
memory.

The first pass derives:

- stable per-read selected orientation and genomic span;
- reference-base identity by position;
- tract-boundary and interrupt observations.

The second pass emits only rows for reads that actually span a validated tract and updates
small summary accumulators.

This keeps memory proportional to read count, reference positions, and summary metric
vectors rather than all joined observations.

## Research questions

The first analysis should answer, separately for HV1 and HV2:

1. Does profile impurity increase after crossing the tract compared with before crossing
   it on the same assay/orientation class?
2. Is post-tract previous-reference-base mass elevated, consistent with an n-1 phase
   shadow?
3. Does the pattern differ when the interrupt observation is T versus C?
4. How does the effect vary with read-order distance and call-order distance?
5. Do opposite-orientation reads covering the same loci avoid the degradation when they
   have not yet crossed the tract?
6. Is there observable evidence of phase recovery, and is recovery read-specific rather
   than a fixed genomic distance?

Only after these descriptive questions are answered should a phase-instability detector
or recovery model be proposed.

## Scientific boundary

This artifact does **not**:

- label a locus or read as artifact;
- infer biological T310C/T16189C genotype;
- infer length heteroplasmy;
- assign a phase-instability score;
- define a recovery distance;
- lower production confidence;
- change placement, read admission, variant eligibility, or sample output.

Those decisions require a separate validated promotion step under ADR-0052.

## Privacy

The artifact remains under ignored `validation-results/`. It contains sample IDs, trace
hashes, assay metadata, signal profiles, and locus-level biological evidence and therefore
inherits the validation corpus sensitive-derived-data policy.
