# Threshold Research Protocol

## Purpose

Define how Signal should research thresholds for nucleotide-profile geometry without
prematurely turning descriptive evidence into biological interpretation.

This document does not establish production thresholds.

## Current metrics under study

Signal currently retains threshold-free metrics at differential loci:

~~~text
within_profile_impurity
between_profile_dispersion
total_profile_heterogeneity
directional_profile_distance
~~~

with:

~~~text
total_profile_heterogeneity
    = within_profile_impurity + between_profile_dispersion
~~~

and directional Total Variation in `[0, 1]` when both orientations contribute.

These metrics are not allele fractions, Phred probabilities, genotype probabilities,
heteroplasmy percentages, or confidence scores.

## Implemented descriptive dataset step

Before any threshold-selection code is introduced, a completed validation corpus is
converted into one hash-bound descriptive research dataset:

```bash
uv run python scripts/analyze_validation_corpus.py \
  --corpus-dir validation-results/corpus \
  --output-dir validation-results/research/baseline
```

The implementation streams the corpus into joined `loci.csv` and
`observations.csv` tables and publishes `signal.validation_research/v1` provenance.
It also reports exact empirical nearest-rank p50/p90/p95/p99 summaries for the four
geometry metrics overall and by holdout/truth/fit grouping.

These percentiles describe observed distributions only. They are **not** candidate
thresholds. Threshold selection remains blocked until the real corpus, null population,
false-positive objective, development split, and locked holdout are reviewed and frozen.

See [research-dataset.md](research-dataset.md) for the implemented table boundary.

## Research order

Research each metric independently before combining them into a multivariate rule.

### 1. Within-profile impurity

Primary question:

> How broad/mixed is nucleotide evidence inside the individual contributing traces?

Use clean homoplasmic controls to define the null distribution and known point-mixture
series to measure response versus prepared mixture level.

### 2. Between-profile dispersion

Primary question:

> How strongly do contributing traces disagree after preserving each trace's internal
> profile shape?

Use:

- clean technical replicates;
- independent PCR replicates;
- deliberately discordant controls;
- artifact challenge cases.

This metric is critical for distinguishing reproducible mixed traces from clean reads that
disagree.

### 3. Directional profile distance

Primary question:

> How different are the forward and reverse mean profile distributions?

Use same-PCR F/R controls first, then independent-PCR and cross-amplicon overlap sets.

Do not interpret a large value as biological strand bias. It is orientation-specific
measurement disagreement until validated otherwise.

## LoB/LoD-style framework

CLSI EP17 provides a useful conceptual distinction:

- **Limit of Blank (LoB):** the upper range expected from truly blank/negative material;
- **Limit of Detection (LoD):** the lowest level that can be detected with a prespecified
  probability under routine conditions;
- **Limit of Quantification (LoQ):** the lowest level that can be quantified with acceptable
  performance.

For Signal:

### Geometry LoB analogue

Estimate the upper distribution of each metric under appropriate negative controls:

~~~text
within impurity:
    clean homoplasmic traces

between dispersion:
    clean replicate traces

directional distance:
    clean F/R pairs
~~~

Use grouped resampling at the independent source/PCR level. Do not bootstrap individual
loci as if they were independent.

A candidate upper-tail threshold may be explored only after the desired false-positive
rate is specified.

### Mixture LoD analogue

After a candidate mixed-signal rule is frozen on development data, estimate detection
probability across known mixture fractions.

The study should report the smallest fraction meeting a prespecified detection
probability with uncertainty bounds. CLSI commonly describes LoD in terms of consistent
detection, typically at or above 95%, but Signal must predeclare its own validation
criterion and dataset before using that terminology.

### LoQ

Do not research LoQ yet.

Current `EvidenceProfile` weights are normalized signal evidence, not validated mixture
fractions. Quantitative heteroplasmy estimation requires a separate calibration model
against truth-known mixtures.

## Threshold-selection discipline

Before viewing the locked holdout:

1. define the biological/operational question;
2. define the null population;
3. define the desired false-positive behavior;
4. define the candidate metric(s);
5. define the selection rule;
6. freeze the rule and threshold;
7. evaluate once on the holdout.

Do not repeatedly tune against the holdout.

## Candidate univariate studies

### Within-mixture candidate threshold

Development experiment:

~~~text
clean controls
    -> distribution of within_profile_impurity

known point mixtures
    -> sensitivity curve versus mixture fraction
~~~

Research outputs:

- empirical clean percentiles;
- source-group bootstrap intervals;
- sensitivity by truth fraction;
- false-positive rate in artifact challenge traces;
- threshold stability by run/amplicon/base-substitution/context.

### Between-disagreement candidate threshold

Development experiment:

~~~text
concordant technical/PCR replicates
    -> null between_profile_dispersion

deliberately discordant reads
    -> positive disagreement distribution
~~~

Research outputs:

- false disagreement rate;
- ability to separate read disagreement from replicated within-trace mixture;
- dependence on contributor count;
- dependence on amplicon/run.

### Directional-distance candidate threshold

Development experiment:

~~~text
clean F/R pairs
    -> null directional_profile_distance distribution

known direction-specific artifact/conflict cases
    -> challenge distribution
~~~

Research outputs:

- upper-tail null behavior;
- F/R reproducibility;
- cross-run and cross-amplicon stability.

Do not use direction labels as an input to read placement.

## Multivariate interpretation research

Only after the univariate behavior is understood should Signal evaluate composite
interpretation rules.

A future qualitative state might use evidence patterns such as:

~~~text
low within + low between + low directional distance
    -> reproducible narrow evidence

high within + low between + low directional distance
    -> reproducible mixed-profile evidence

low within + high between
    -> inter-read disagreement

high directional distance
    -> direction-specific disagreement evidence
~~~

These are hypotheses for validation, not production enum definitions.

Never optimize a classifier to call heteroplasmy directly before explicitly including
artifact and contamination challenge classes.

## Performance reporting

For every candidate rule report:

- independent source-group count;
- PCR replicate count;
- sequencing run/instrument count;
- loci evaluated;
- true positives;
- false positives;
- true negatives;
- false negatives;
- sensitivity with confidence interval;
- specificity with confidence interval;
- false positives per 1,000 or 10,000 evaluated clean loci;
- sample-level probability of at least one false positive;
- repeatability;
- reproducibility;
- performance by mixture fraction;
- performance by substitution class;
- performance by amplicon and read position;
- performance in artifact-tagged regions;
- performance in candidate-noisy regions.

ROC or precision-recall curves are exploratory summaries only. A final threshold must be
chosen from a predeclared use-case/error requirement, not from maximum F1 alone.

## Uncertainty and clustered data

Observations are nested:

~~~text
source
  -> PCR replicate
      -> sequencing run
          -> trace
              -> locus
~~~

Confidence intervals and resampling must respect that hierarchy.

At minimum, bootstrap or split at the highest independent source group relevant to the
claim. Locus-wise random resampling will overstate precision.

## Threshold stability

A single global threshold is acceptable only if validation shows acceptable stability
across the intended operating domain.

Explicitly test interaction with:

- instrument/capillary;
- sequencing run;
- amplicon;
- direction;
- trace position;
- nucleotide substitution class;
- local sequence context;
- total signal;
- SNR;
- candidate-noisy membership.

If a metric requires assay/run-specific stratification, encode that as validation
provenance rather than pretending a universal threshold exists.

## Literature anchors

Published Sanger results demonstrate why Signal should not import a universal percentage
cutoff:

- A controlled complete-mtDNA mixture study reported Sanger detection down to about 7%
  in its setup.
- Another mtDNA study found SeqScape detected 10% mixtures while 2% and 5% were not
  detected under its settings.
- NIST SRM 2394 provides certified point-mixture materials at 1%, 2.5%, 5%, 10%, 20%,
  30%, 40%, and 50%.
- Other work observed 10-20% Sanger mixtures as barely visible while 30-50% were clear.

These results define useful challenge levels, not Signal performance claims.

References:

- https://pmc.ncbi.nlm.nih.gov/articles/PMC4532422/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC3788774/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC3486893/
- https://tsapps.nist.gov/srmext/certificates/archives/2394.pdf

## Separate point and length-mixture studies

Do not fit point-mixture thresholds using poly-C/indel/length-mixture loci.

Length mixture can create downstream phase-shifted chromatograms and depends strongly on
repeat context and alignment interpretation. It needs a separate validation protocol.

The point-mixture study may record these loci but must exclude them from threshold fitting.

## Promotion criteria

A candidate threshold remains research until:

1. the corpus definition is frozen;
2. the development/holdout grouping is frozen;
3. truth provenance is reviewed;
4. the threshold-selection objective is predeclared;
5. the threshold is selected without holdout tuning;
6. holdout performance is documented;
7. run/amplicon/context stability is assessed;
8. artifact and contamination challenges are evaluated;
9. limitations are documented;
10. a separate ADR/SRS change explicitly promotes the threshold.

Until then production continues to expose only threshold-free evidence geometry.
