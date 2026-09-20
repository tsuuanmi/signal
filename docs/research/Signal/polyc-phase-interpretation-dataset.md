# Poly-C Phase Interpretation Dataset

## Purpose

Prepare one deterministic, development-only research dataset for the phase-interpretation
study without moving threshold selection or classification into the production runtime.

The artifact joins:

```text
signal.validation_corpus/v1
        +
signal.validation_phase_hypotheses/v1
        ↓
signal.validation_phase_interpretation_dataset/v1
```

Python remains research/validation tooling only. The production scientific authority
remains the Rust `signal.polyc_phase/v1` measurement. Any later interpretation rule must
be frozen from development research and implemented authoritatively in Rust before it can
affect production behavior.

## Command

Partition names are explicit study inputs. No default holdout-group semantics are assumed.

```bash
uv run python scripts/prepare_phase_interpretation_dataset.py \
  --corpus-dir validation-results/corpus \
  --hypotheses-dir validation-results/research/polyc-phase-hypotheses/rust-v1 \
  --output-dir validation-results/research/phase-interpretation-dataset/rust-v1 \
  --development-group development \
  --holdout-group holdout \
  --unassigned-group unassigned
```

Repeat any group option when the local manifest uses multiple group names for one study
partition.

Every observed `holdout_group` must be declared exactly once as development, holdout,
excluded, or unassigned. Unknown groups are rejected rather than silently admitted.

## Source validation

The preparation layer reuses the existing validated corpus loader and shared phase-artifact
loader.

Before publication it requires exact agreement for:

- source corpus index SHA-256;
- manifest SHA-256;
- Signal version;
- reference SHA-256;
- configuration SHA-256;
- validation-case identity;
- read SHA-256;
- read amplicon metadata;
- selected orientation reconstructed from validated corpus measurements.

The phase-hypothesis method must match the production
`signal.polyc_phase/v1` constants:

```text
window size = 25 profile-bearing observations
window step = 5 profile-bearing observations
candidate offsets = -5..-1,+1..+5
```

No second manifest parser, phase-window generator, candidate calculation, filename join, or
declared-direction placement fallback is introduced.

## Output

```text
validation-results/research/phase-interpretation-dataset/<study>/
├── index.json
├── development-windows.csv
├── development-candidates.csv
└── readiness.csv
```

The directory is no-overwrite and hash-bound to both source indexes and all generated
tables.

### `development-windows.csv`

Contains only windows whose case:

```text
declared study partition == development
AND
include_in_threshold_fit == true
```

Each row joins the authoritative phase window to the existing validation metadata needed
for research:

- case/source/specimen identity;
- truth/proxy provenance;
- mixture metadata when present;
- read/PCR/run/instrument/amplicon metadata;
- artifact tags and declared direction as metadata only;
- selected orientation from Signal;
- tract and observed interrupt evidence;
- exact window geometry and call-index bounds;
- profile/noisy counts;
- mean impurity and zero-reference mass.

The table defines no state, winner, threshold, persistence rule, recovery rule, or weight.

### `development-candidates.csv`

Retains the complete source candidate curve for every admitted development window:

- `window_id`;
- candidate reference offset;
- informative-position count;
- zero-reference mass;
- shifted-reference mass;
- residual mass.

It deliberately avoids duplicating case/read/truth metadata ten times per window. Join
candidate rows to `development-windows.csv` by `window_id`.

No candidate is selected or ranked.

### `readiness.csv`

Contains aggregate counts only, including locked holdout/excluded/unassigned partitions.

Rows are stratified by:

```text
partition
holdout_group
include_in_threshold_fit
truth_class
tract
selected orientation
amplicon
observed interrupt base
```

and report counts for:

- cases;
- source groups;
- specimen groups;
- PCR replicates;
- sequencing runs;
- instruments;
- reads;
- read/tracts;
- windows;
- candidate rows.

No continuous holdout phase measurements are exported.

The index also records partition-level counts, including cases/reads with no complete phase
window, so absence of windows remains visible instead of disappearing from readiness
review.

## Anti-leakage boundary

This artifact does not expose holdout window/candidate masses for rule development.

Holdout source artifacts still exist locally as validation evidence, but the preparation
tool intentionally does not copy those continuous features into the development dataset.

`include_in_threshold_fit=false` excludes a development-partition case from the fitting
tables while keeping it visible in aggregate readiness counts.

Source-group partition consistency remains enforced by the validation corpus loader.

## Independence counts

PCR replicate counts are qualified by source group so a locally reused replicate label does
not collapse independent sources into one nominal replicate.

Window counts are descriptive only. Overlapping windows from one trace are correlated and
must never be treated as independent validation samples.

## Scientific boundary

The artifact does not:

- fit a threshold;
- define a phase state;
- choose a winning offset;
- derive a recovery rule;
- expose holdout continuous phase features;
- infer genotype, indel length, length heteroplasmy, contamination, or artifact truth;
- alter Rust measurement;
- alter calls, variants, eligibility, weighting, or no-call behavior;
- change configuration or public schemas.

The next step is development-only exploratory rule research using this frozen joined
dataset. If a rule survives development and untouched holdout evaluation, production
promotion returns to the Rust core as specified in
[polyc-phase-interpretation-study.md](polyc-phase-interpretation-study.md).
