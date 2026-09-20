# Poly-C Recurrent-Locus Phase Context

## Purpose

Join recurrent mtDNA loci observed during ADR-0054 research back to the exact
post-poly-C phase windows and complete candidate curves that contain those loci.

The fixed recurrent positions are:

```text
253
297
302
16194
16197
```

This artifact exists to answer a descriptive question:

> When one of these loci is observed after a supported poly-C tract, which exact
> profile-bearing source windows contain it, and what candidate-offset evidence exists
> both for the whole window and at that locus?

It does not decide that any recurrent locus is an artifact, phase marker, or biological
variant.

## Inputs

Two completed, hash-bound artifacts are required:

```text
signal.validation_polyc_phase/v1
signal.validation_phase_hypotheses/v1
```

The phase-hypothesis index must SHA-256 bind the supplied poly-C phase index. Corpus,
Signal, manifest, reference, and configuration identities must also agree.

## Exact window membership

Membership is not inferred from:

```text
window_start_distance <= locus_distance <= window_end_distance
```

because phase windows are defined over consecutive **profile-bearing observations** and
may cross gaps where an observation has no profile.

Instead the analysis reconstructs windows from the source poly-C observations using the
same authoritative phase-window generator and the exact window size/stride declared by
the source phase-hypothesis method. The reconstructed window IDs, metadata, noisy counts,
mean impurity, and zero-reference mass must match the immutable source window table.

Only then is a recurrent observation joined to windows in which that exact observation
is a member.

A recurrent post-tract observation without a profile remains in `loci.csv` with zero
containing windows. It is never assigned membership from an interval approximation.

## Command

```bash
uv run python scripts/analyze_polyc_phase_recurrent_loci.py \
  --phase-dir validation-results/research/polyc-phase/circular-v1 \
  --hypotheses-dir validation-results/research/polyc-phase-hypotheses/circular-v1 \
  --output-dir validation-results/research/polyc-phase-recurrent-loci/circular-v1
```

The output directory must not already exist.

## Output

```text
validation-results/research/polyc-phase-recurrent-loci/circular-v1/
├── index.json
├── loci.csv
├── windows.csv
└── candidates.csv
```

### `loci.csv`

One row per post-tract observation at a recurrent position preserves:

- case/read/tract/amplicon/orientation identity;
- observed interrupt base;
- recurrent rCRS position and exact read-order distance;
- call index, reference base, state, and aligned base;
- noisy-region membership;
- normalized A/C/G/T profile when available;
- profile impurity and reference-base mass when available;
- number of exact source windows containing that observation.

Profile-missing observations remain explicit with empty profile-derived fields.

### `windows.csv`

One row per:

```text
recurrent observation × exact containing source window
```

preserves the recurrent-locus identity plus:

- source window ID;
- exact source window start/end distance;
- profile/noisy-observation counts;
- source window mean impurity and zero-reference mass;
- recurrent-locus impurity, reference-base mass, and noisy context.

No interval-only membership is emitted.

### `candidates.csv`

One row per:

```text
recurrent observation × containing window × declared candidate offset
```

retains the complete source candidate curve:

- candidate offset;
- source window informative-position count;
- source window zero-reference, shifted-reference, and residual masses;
- whether the recurrent locus itself is informative for that candidate;
- shifted reference base at the recurrent locus when informative;
- exact recurrent-locus zero-reference, shifted-reference, and residual masses.

The per-locus contribution uses the same authoritative candidate contribution primitive as
window-level phase-hypothesis aggregation.

If the shifted reference position is unavailable, the shifted reference base equals the
zero-phase reference base, or the recurrent observation has no profile, the locus is
non-informative for that candidate and locus candidate masses remain empty.

## Interpretation

This artifact can support questions such as:

- does position 16194 occur inside windows with elevated shifted-reference mass?
- for the same candidate offset, does the locus itself contribute shifted-reference mass
  in the same direction as the surrounding window?
- is position 253 profile-bearing but outside all complete source windows, or is it an
  exact member of one or more?
- do C-interrupt and T-interrupt reads expose different candidate context at the same
  recurrent position?

Those questions remain descriptive. The complete candidate curve is retained so no
single offset is promoted to a phase call.

## Scientific boundary

This artifact does not:

- assign a recurrent-locus artifact or truth label;
- select a winning candidate offset;
- define a coherence score or recurrent-locus score;
- infer genotype, indel, or biological length heteroplasmy;
- define a phase state, classifier, breakpoint, or recovery interval;
- define confidence attenuation, evidence weighting, demixing, or a no-call rule;
- tune against holdout truth;
- modify production Rust behavior or public result schemas.

With exact recurrent-locus context, parameter sensitivity, opposite-orientation controls,
and threshold-free explainability all represented as separate descriptive artifacts,
ADR-0054's planned descriptive research surface is complete. Any production phase-state
model is a separate promotion decision.
