# Validation Audit Strata

## Purpose

Create a deterministic review shortlist from a completed validation corpus without turning
corpus-relative outliers into biological truth, sample QC rejection, or production
thresholds.

The audit is downstream of the descriptive research dataset:

```text
signal.validation_corpus/v1
        │
        ├── validation logs
        │
        └── signal.validation_research/v1
                    │
                    ▼
          signal.validation_audit/v1
```

## Command

```bash
uv run python scripts/audit_validation_corpus.py \
  --corpus-dir validation-results/full-20260919 \
  --research-dir validation-results/research/full-20260919 \
  --output-dir validation-results/audit/full-20260919
```

The output directory must not already exist.

## Output

```text
validation-results/audit/full-20260919/
├── index.json
├── read-audit.csv
├── locus-audit.csv
└── case-audit.csv
```

### `read-audit.csv`

One row per corpus read, binding deterministic validation-log metrics back to the corpus
read SHA-256 and manifest acquisition metadata.

The table includes:

- case/read SHA-256 identity;
- sequencing run, amplicon, and declared direction;
- inferred orientation;
- calls/profiled loci/noisy calls and noisy-call fraction;
- retained trim bounds and retained fraction;
- callable columns/identity, mismatches, and gap opens;
- excluded variant-candidate count;
- empirical stratum boundaries where the stratum is benchmarked;
- observational audit flags.

Read strata are defined by:

```text
amplicon_id × declared_direction
```

The four relative outlier flags require at least 20 reads in the stratum:

| Flag | Review rule |
|---|---|
| `alignment_challenge` | callable identity ≤ empirical p05 |
| `high_noise` | noisy-call fraction ≥ empirical p95 |
| `aggressive_trim` | retained fraction ≤ empirical p05 |
| `short_coverage` | callable columns ≤ empirical p05 |

Percentiles use the exact empirical nearest-rank rule.

A smaller stratum is marked `unbenchmarked_stratum`; it does not borrow thresholds from
another primer/direction group.

`orientation_disagreement` means selected orientation differs from the manifest's
declared-direction metadata. Declared direction remains validation metadata and never
drives placement.

### `locus-audit.csv`

Contains every locus with both reference and alternate read observations. It preserves
profile geometry plus context for alternate observations:

- alternate observation count and orientation counts;
- noisy alternate observations;
- retained-read edge distance using each observation's original call index and that read's
  validated trim bounds;
- whether alternate evidence occurs in both selected orientations.

`edge_discordance` is set when at least one alternate observation is within 10 calls of
a retained trim edge and alternate support is not present from both orientations.

This is an audit context flag, not an artifact verdict.

### `case-audit.csv`

One row per validation case with:

- read/locus counts;
- alternate and mixed-locus counts;
- noisy and bidirectional-locus counts;
- p95 profile-geometry summaries;
- minimum alignment identity / retained fraction / callable columns;
- maximum read noise rate;
- counts of each read-level audit flag;
- mixed-locus edge-discordance count;
- case-level review flags.

`short_coverage_cluster` requires at least two `short_coverage` reads in the case.

`geometry_challenge` means that the case p95
`total_profile_heterogeneity` is at or above the empirical p95 across case-level p95
values. It is a corpus-relative review stratum only.

## Provenance

`index.json` is `signal.validation_audit/v1` and records:

- source corpus index SHA-256;
- source research index SHA-256;
- Signal/manifest/reference/configuration identities;
- exact audit method constants;
- empirical read-stratum boundaries and sample counts;
- the corpus-relative geometry boundary;
- row counts, column contracts, SHA-256, and flag counts for all three audit tables.

The audit parser consumes only deterministic read-stage metrics from validation logs and
binds them to corpus reads by SHA-256. It does not copy timestamps, run IDs, local paths,
or raw log lines.

## Scientific boundary

Audit flags answer:

> Which reads, loci, and cases deserve explicit review before truth curation and threshold
> research?

They do **not** answer:

> Is this read bad?
> Is this locus an artifact?
> Is this sample heteroplasmic?
> Should this case be excluded?
> What production threshold should Signal use?

The manifest remains the only source for truth provenance, threshold-fit inclusion, and
development/holdout grouping.

## Recommended curation workflow

1. Generate the completed corpus.
2. Generate the descriptive research dataset.
3. Generate audit strata.
4. Review `case-audit.csv` as the shortlist.
5. Inspect relevant `read-audit.csv`, `locus-audit.csv`, original chromatograms, and
   independent truth sources.
6. Update the local manifest only when an independent curation decision is made.
7. Freeze the development/holdout split before threshold selection.
8. Follow [threshold-research.md](threshold-research.md) for candidate-rule research.

## Privacy

Audit outputs remain sensitive derived biological data. They omit local AB1 paths but
retain trace hashes, sample IDs, acquisition metadata, signal quality, alignment metrics,
and locus-level evidence. They remain ignored under `validation-results/` and inherit the
same approval, retention, and redistribution policy as the source corpus.
