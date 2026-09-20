# Poly-C Candidate Phase Hypotheses

## Purpose

Distinguish two different post-poly-C failure modes without changing production calling:

1. **structured dephasing** — downstream A/C/G/T evidence is substantially explained by
   the normal reference phase plus a stable integer reference offset;
2. **unstructured degradation** — substantial profile mass remains unexplained by both
   the normal and tested shifted reference phases.

This research implements ADR-0054 and consumes the immutable
`signal.validation_polyc_phase/v1` artifact. It does not reopen AB1 files or recompute
poly-C geometry.

## Tracy lesson

Tracy's `decompose` path first detects a persistent signal transition, then evaluates
multiple downstream insertion/deletion offsets and records how well each candidate makes
the downstream primary/secondary evidence compatible with the reference.

Signal adopts the **candidate explanatory curve** and **downstream persistence** ideas.
It does not adopt Tracy's diploid two-allele interpretation, reference-driven basecall
rewriting, or Tracy's breakpoint/MAD thresholds.

Source audited:

- <https://github.com/gear-genomics/tracy/blob/master/src/decompose.h>

## Candidate evidence

For a profile-bearing post-tract observation at reference phase `i`, a candidate integer
offset `k` looks at the reference base `k` positions away in selected sequencing order.

A position is informative only when:

```text
reference(i) != reference(i + k)
```

At each informative position the normalized EvidenceProfile is partitioned into:

```text
zero_phase_mass     = mass(reference(i))
shifted_phase_mass  = mass(reference(i + k))
residual_mass       = 1 - zero_phase_mass - shifted_phase_mass
```

This yields two separable questions:

- is there coherent mass on a specific shifted reference sequence?
- after allowing that shift, how much evidence still cannot be explained?

Low residual does not prove an indel or biological length heteroplasmy. High residual does
not by itself prove that a read is unusable. Both remain descriptive validation evidence.

## Windows

The first research method uses fixed windows of profile-bearing observations after the
tract. Defaults are intentionally research parameters rather than production constants:

```text
window size = 25 profile observations
window step = 5 profile observations
candidate offsets = -5..-1 and +1..+5 reference positions in read order
```

Every output index records the exact values. Sensitivity to these parameters must be
checked before any detector or threshold is promoted.

Windows are evaluated over consecutive post-tract observations from one read/tract pair.
A single focal variant therefore cannot create strong phase evidence unless the same
reference offset explains surrounding profiles as well.

## Command

```bash
uv run python scripts/analyze_polyc_phase_hypotheses.py \
  --phase-dir validation-results/research/polyc-phase/full-20260919 \
  --output-dir validation-results/research/polyc-phase-hypotheses/full-20260919
```

Optional research parameters:

```text
--window-size
--window-step
--max-offset
```

## Output

```text
validation-results/research/polyc-phase-hypotheses/full-20260919/
├── index.json
├── windows.csv
└── hypotheses.csv
```

### `windows.csv`

One row per complete downstream window:

- case/read/tract identity;
- amplicon, selected orientation, and observed interrupt base;
- start/end distance from the tract;
- start/end call index when available;
- profile and noisy-observation counts;
- mean profile impurity;
- mean mass on the unshifted reference.

### `hypotheses.csv`

One row per window × non-zero candidate offset:

- candidate reference offset in sequencing order;
- number of informative positions;
- mean unshifted-reference mass on those positions;
- mean candidate-shifted-reference mass;
- mean residual mass.

Candidates with zero informative positions remain present with empty mass metrics so the
complete tested curve is explicit.

The artifact deliberately contains no `best_shift`, phase score, classifier, recovery
state, or confidence weight.

## How this addresses the two post-poly-C mechanisms

Expected qualitative patterns:

| Pattern | Shifted mass | Residual | Interpretation to investigate |
|---|---:|---:|---|
| clean phase | low | low | unaffected / phase coherent |
| structured dephasing | elevated for stable offset | low | sequence-offset mixture may remain informative |
| degraded | no stable offset | high | simple phase model does not explain signal |
| shifted + degraded | elevated | high | partial phase structure plus substantial corruption |

These are research interpretations only. No numeric boundaries are defined.

## Next analyses

On the full corpus:

1. compare candidate curves for observed T versus C at T310/T16189;
2. test whether the same offset persists across adjacent windows of one read;
3. compare post-tract windows with overlapping opposite-orientation pre-tract evidence;
4. measure candidate/residual trajectories with distance from the tract;
5. inspect whether recurrent loci 253, 297, 302, 16194, and 16197 fall inside windows
   with coherent shifted-reference support;
6. identify reads where impurity is high but no candidate offset explains the profiles.

Only after those analyses should Signal consider a phase-state detector, recovery model,
evidence attenuation, demixing, or a no-call policy.

## Scientific boundary

This research does not:

- infer an insertion/deletion length;
- infer biological length heteroplasmy;
- demix or rewrite sequence;
- select a winning phase;
- define a breakpoint;
- define a phase-recovery distance;
- lower or remove production evidence;
- change any Rust scientific-core behavior.
