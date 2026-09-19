# Validation Research Dataset

## Purpose

Define the implemented local data-preparation boundary between a completed validation
corpus and empirical threshold research.

This tooling is descriptive only. It does not establish or recommend a production
threshold.

## Command

Build a joined research dataset from a completed corpus:

```bash
uv run python scripts/analyze_validation_corpus.py \
  --corpus-dir validation-results/corpus \
  --output-dir validation-results/research/baseline
```

The output directory must not already exist.

## Output

```text
validation-results/research/baseline/
├── index.json
├── loci.csv
└── observations.csv
```

### `index.json`

`signal.validation_research/v1` records:

- SHA-256 of the source corpus `index.json`;
- Signal, manifest, reference, and configuration identities;
- row counts and SHA-256 for both CSV tables;
- exact table column lists;
- descriptive statistics for the current geometry metrics.

No local AB1 filesystem path is copied into the research dataset.

### `loci.csv`

One row per validation locus, preserving:

- validation case and source/specimen grouping;
- truth class/method/locus/alleles/prepared mixture metadata;
- threshold-fit inclusion and holdout group;
- approval/redistribution metadata;
- whether the current row is the manifest-declared truth locus;
- complete `signal.validation_locus/v2` locus-level counts, mean profiles, profile
  geometry, directional distance, and missing/noisy/deletion observation counts.

The nested `observations[]` payload is not duplicated in this table.

### `observations.csv`

One row per read observation at one validation locus. It joins:

- case/truth/holdout metadata;
- locus coordinate/reference base;
- read SHA-256;
- PCR replicate, sequencing run, instrument, amplicon, declared direction, and artifact
  tags from the corpus index;
- selected orientation/state/base/quality;
- call/PLOC/window/primary-peak/event coordinates and offsets;
- reference-oriented per-channel peak position/height/source;
- primary-event channel heights;
- corrected amplitude, SNR, and profile A/C/G/T values;
- candidate-noisy-region membership.

A/C/G/T vectors are flattened into explicit `*_a`, `*_c`, `*_g`, and `*_t`
columns for straightforward dataframe/statistical-tool ingestion.

## Validation and provenance checks

Before a row is emitted the tooling verifies:

- corpus, manifest, and measurement schema versions;
- corpus Signal/reference/configuration identities;
- exact canonical `cases/<validation_case_id>.jsonl` paths;
- declared case and trace counts;
- unique trace SHA-256 ownership;
- source-group holdout consistency;
- measurement Signal/reference/configuration identity;
- measurement locus count;
- strictly increasing positive locus coordinates;
- read observation membership;
- fixed `signal.validation_locus/v2` locus/observation field sets;
- finite scalar/vector numeric values used by the research tables.

Existing research output is never overwritten. A publication failure removes the newly
created destination rather than leaving a completed-looking dataset.

## Descriptive statistics

The research index summarizes:

```text
within_profile_impurity
between_profile_dispersion
total_profile_heterogeneity
directional_profile_distance
```

For each metric it reports non-missing/missing counts, minimum, mean, empirical p50, p90,
p95, p99, and maximum.

Percentiles use the exact empirical **nearest-rank** rule with no interpolation.

Summaries are provided for:

- all loci;
- loci whose case has `include_in_threshold_fit=true`;
- each unique combination of holdout group, truth class, and threshold-fit inclusion.

These percentiles are descriptive distribution summaries, not candidate cutoffs.

## Scale behavior

Joined rows are streamed case by case directly to CSV. The implementation does not retain
all locus/observation dictionaries in memory.

Exact metric samples are retained only as compact double arrays so empirical percentiles
remain exact while memory use scales with four numeric vectors rather than the full joined
dataset.

## Privacy

The CSV tables and research index remain under ignored `validation-results/` and inherit
the AB1/corpus privacy policy. Hashes, truth metadata, and biological geometry can still be
identifying even though local trace paths are omitted.

## Next research step

After the real corpus is reviewed and the development/holdout split plus false-positive
objective are frozen, a separate threshold-selection study may consume this dataset.

That later step must follow [threshold-research.md](threshold-research.md) and must not
tune repeatedly against the locked holdout.
