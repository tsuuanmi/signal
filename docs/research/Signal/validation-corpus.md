# Validation Corpus Design

## Purpose

Define the local validation corpus needed before Signal promotes any nucleotide-profile
geometry threshold into production interpretation.

This document is research guidance. It does not define current production behavior,
clinical performance, heteroplasmy detection limits, or release claims.

## Validation principle

Thresholds must come from Signal's own internal validation data, not from a cutoff
copied from another laboratory, instrument, chemistry, or analysis package.

The 2024 SWGDAM mitochondrial-DNA interpretation guidelines require laboratory
interpretation criteria and thresholds to be supported by applicable internal validation.
They also recommend forward/reverse sequencing, careful review of overlapping
sequences/amplifications, and Sanger evaluation that considers signal intensity,
background noise, peak resolution/shape, and sequencing or amplification artifacts.

Useful external anchors:

- SWGDAM, Interpretation Guidelines for Mitochondrial DNA Analysis by Forensic DNA
  Testing Laboratories (2024):
  https://www.swgdam.org/_files/ugd/4344b0_9784320e1188491fbdd0dbf040ca69ae.pdf
- SWGDAM, Validation Guidelines for DNA Analysis Methods (2016):
  https://www.swgdam.org/_files/ugd/4344b0_813b241e8944497e99b9c45b163b76bd.pdf
- NIST SRM 2394, Heteroplasmic Mitochondrial DNA Mutation Detection Standard:
  https://tsapps.nist.gov/srmext/certificates/archives/2394.pdf
- CLSI EP17, Evaluation of Detection Capability for Clinical Laboratory Measurement
  Procedures: https://clsi.org/shop/standards/ep17/

Literature reports materially different Sanger mixed-signal detection performance across
experiments. Published examples include approximately 7% detection in one controlled
mtDNA mixture experiment, complete software detection at 10% but not 2-5% in another,
and chromatograms where 10-20% mixtures were only weakly visible while 30-50% were
clear. These are validation examples, not transferable Signal thresholds.

## Scientific questions

The corpus must independently test whether Signal can measure:

1. clean single-nucleotide evidence;
2. reproducible within-trace mixed nucleotide evidence;
3. disagreement between independently observed traces;
4. forward/reverse profile disagreement;
5. cross-amplicon consistency;
6. technical artifacts that mimic mixed signal;
7. repeatability and reproducibility across runs and PCR preparations;
8. point-mixture behavior separately from length/indel mixture behavior.

The corpus must not collapse these questions into one generic heteroplasmy label.

## Corpus strata

### A. Clean homoplasmic controls

Purpose:

- define the empirical null distribution of within-profile impurity;
- define baseline between-read dispersion;
- define baseline forward/reverse Total Variation distance;
- quantify false-positive geometry in ordinary high-quality sequence.

Prefer samples with independently established sequence truth and broad coverage across
the validated mtDNA regions.

Include variation across:

- nucleotide identity;
- neighboring sequence context;
- amplicon;
- read orientation;
- trace position from early to late read;
- sequencing run;
- capillary/instrument when available.

### B. Same-PCR forward/reverse pairs

Purpose:

- characterize direction-specific technical variation;
- establish the null distribution of directional profile distance;
- measure how often F/R disagreement appears without biological replication.

Forward and reverse traces from one PCR product are technical observations, not
independent biological replicates.

### C. Technical resequencing replicates

Repeat sequencing of the same PCR product across available:

- capillaries;
- injections;
- sequencing plates/runs;
- operators;
- instruments.

Purpose:

- estimate repeatability;
- isolate sequencing-stage variance from PCR-stage variance.

### D. Independent PCR replicates

Independent amplifications from the same source DNA.

Purpose:

- measure reproducibility across PCR preparation;
- test whether mixed-profile geometry reproduces across independent amplification;
- distinguish persistent sample evidence from PCR-specific artifacts.

### E. Known point-mixture series

Use truth-known mixtures spanning the expected Sanger transition region.

A useful design grid, inspired by NIST SRM 2394 and published mtDNA validation work, is:

~~~text
0%
2.5%
5%
10%
15%
20%
30%
40%
50%
~~~

The exact levels may be adjusted to available materials, but the study must include:

- true zero-mixture controls;
- multiple levels below the expected detection region;
- multiple levels around the transition region;
- high mixtures approaching 50%.

Prefer multiple independent source-template pairs and multiple substitution classes rather
than one favorable locus.

Record whether the known fraction is based on mass mixture, molecule count, orthogonal
sequencing, or another truth method. Do not assume a prepared mass fraction equals the
observed chromatogram peak fraction.

### F. Cross-amplicon overlap controls

Use loci independently covered by different amplicons.

Purpose:

- test whether the same locus geometry is stable across primer/amplicon context;
- identify amplicon-specific artifacts;
- validate the generic N-read model rather than only F/R pairs.

### G. Artifact challenge set

Deliberately retain difficult but interpretable traces, including where available:

- low total signal;
- high background;
- broad or poorly resolved peaks;
- compressed peaks;
- baseline drift;
- isolated impulse/spike artifacts;
- read-end degradation;
- neighboring strong-peak interference;
- candidate-noisy regions;
- primer-proximal sequence;
- homopolymer-adjacent point substitutions.

These cases are essential negative controls for mixed-signal thresholds.

### H. Length/indel and homopolymer set

Keep this stratum separate from point-substitution threshold fitting.

Include:

- HVI/HVII poly-C regions;
- known insertions/deletions;
- length-mixture traces where downstream phase shift is visible;
- repeat-associated normalization ambiguities.

Point-profile geometry cannot by itself validate length heteroplasmy. SWGDAM specifically
requires software/repeat handling and length-variant interpretation to be characterized
for the sequencing method and analysis system.

### I. Mixed-source/contamination challenge set

If approved material exists, include deliberate mixtures of different samples.

Purpose:

- test whether sample mixture can mimic a persistent mixed nucleotide locus;
- prevent a future biological-mixture classifier from equating every reproducible mixed
  signal with heteroplasmy.

This stratum is for discrimination research, not for calibrating heteroplasmy fraction.

## Minimum metadata model

The real corpus remains local and ignored. A validation manifest should use
non-identifying research IDs and record at least:

~~~text
validation_case_id
source_group_id
specimen_group_id
pcr_replicate_id
sequencing_run_id
instrument_id
amplicon_id
trace_sha256
declared_direction            # validation metadata only; never placement input
truth_class
truth_method
truth_locus
truth_reference
truth_alternate
known_mixture_fraction
artifact_tags
include_in_threshold_fit
holdout_group
approval_record
redistribution_status
notes
~~~

Fields may be null when not applicable, but absence must be explicit.

`declared_direction` is validation metadata only. Signal must continue deriving
orientation from alignment.

## Truth hierarchy

Preferred truth sources, strongest first:

1. certified reference material or independently characterized standard;
2. orthogonal high-depth validated sequencing;
3. independently repeated PCR plus bidirectional Sanger review with documented analyst
   agreement;
4. synthetic/reference fixture with exact construction truth;
5. expert visual review.

Visual review alone is insufficient for quantitative mixture-fraction calibration.

Every truth record must preserve method and provenance.

## Anti-leakage grouping

Threshold development and holdout evaluation must split by independent source groups,
not by individual locus row.

Never place correlated observations from the same underlying source/PCR series on both
sides of a threshold-selection boundary.

At minimum group together:

- all traces from the same biological source;
- all ratios from one synthetic source-template pair when evaluating generalization to
  new template pairs;
- repeated injections/runs of the same PCR product.

Additional stress tests should leave out whole:

- sequencing runs;
- amplicons;
- substitution classes;
- sequence-context families.

A threshold that works only after trace/locus leakage is not validated.

## Corpus balance

Do not optimize for equal class counts. Preserve enough clean data to estimate rare
false positives and enough mixture/artifact examples to characterize failure modes.

Report both:

- locus-level event counts;
- independent source/PCR/run counts.

Ten thousand correlated locus observations are not equivalent to ten thousand
independent experiments.

## Privacy and repository policy

Real AB1 files, sample IDs, patient metadata, truth spreadsheets, derived per-locus
measurements, and local validation manifests remain outside Git or under ignored local
paths.

Repository documentation may contain only:

- synthetic examples;
- aggregate study-design counts;
- hashes/provenance identifiers that have been explicitly approved for publication.

## Promotion gate

No production threshold may be proposed until the corpus contains:

- clean negative controls;
- at least one independent holdout block;
- both sequencing directions where biologically/assay appropriate;
- technical and independent-PCR replication;
- known point-mixture levels around the candidate transition region;
- artifact challenge examples;
- separate repeat/indel coverage.

The threshold study must document any missing stratum as a limitation.
