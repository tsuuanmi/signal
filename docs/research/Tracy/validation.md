# Tracy Research Validation Strategy

Tracy is a design and benchmark reference, not biological ground truth. The source audit also shows that some Tracy behaviors are deliberate engineering compromises rather than properties Signal should reproduce.

## Validation ladder

### Level 1: deterministic unit tests

Isolate one invariant at a time:

```text
peak localization
PLOC/window bounds
co-localization
profile normalization
zero/flat evidence
fixed-point/quantized profile scoring
orientation tie behavior
profile reverse complement
gap placement tie behavior
change-point candidate search
coordinate provenance
```

### Level 2: synthetic chromatogram shapes

Generate controlled signal arrays containing:

```text
clean single peaks
double peaks
offset neighboring peaks
compressed spacing
baseline drift
saturation/clipping
broad high-amplitude dye-blob-like artifact
low amplitude
one extreme outlier over otherwise usable sequence
phase shift after insertion
phase shift after deletion
homopolymer/poly-C ambiguity
premature/suspicious PLOC termination
```

The expected result should state whether each case is a valid call, ambiguous
evidence, artifact observation, unsupported input, or review candidate.

### Level 3: pairwise conflict corpus

Before forward/reverse consensus is promoted, include controlled two-read cases:

```text
high-quality canonical agreement
primary disagreement with overlapping secondary evidence
one high-quality call vs one weak/ambiguous call
canonical base vs low-quality insertion
gap vs nucleotide conflict
orientation tie or near-tie
short overlap below admission threshold
adequate overlap with poor agreement
```

This specifically addresses failure modes exposed by Tracy issues #50, #58, and #85.

### Level 4: provenanced real AB1 corpus

Critical cases:

```text
clean mtDNA reads
forward/reverse pairs
origin-crossing circular alignments
poly-C regions
known indels
poor-quality reads
known mixed traces
amplicon overlaps
high-amplitude artifacts if approved examples are available
incomplete/suspicious instrument peak-location metadata if available
```

Each file should have source, opaque sample identity, assay context, truth status,
expected region/direction, reference, instrument/run metadata where permitted,
and a documented reason it belongs in the corpus.

### Level 5: independent truth

For claims beyond basic primary-sequence differences, use independent truth where possible:

```text
NGS
clonal sequencing
synthetic mixtures
validated reference materials
replicate assays
```

A second interpretation of the same Sanger trace is not independent truth.

## Benchmark against current Signal

Every new stage should compare against current Signal.

Metrics include:

```text
successful decode/call rate
alignment success rate
orientation accuracy
call retention
false ambiguity rate
artifact false-pass / false-reject rate
variant concordance
indel concordance
origin-crossing correctness
manual-review burden
runtime and memory
```

The new system should not silently degrade clean-read performance.

## Benchmark against Tracy

Tracy remains useful as a comparator for:

```text
basecalls
ambiguity calls
trim bounds
profile orientation
alignment
pairwise consensus
assembly layout
mixed-indel breakpoint candidates
variant coordinate provenance
```

The goal is not compatibility. For every material disagreement, classify it as:

1. Signal regression;
2. intentional Signal correction or stronger invariant;
3. unresolved evidence/model difference;
4. known Tracy limitation.

Known comparison cases already include:

- high-amplitude artifact handling (Tracy issue #116);
- incomplete machine peak-location series (issue #91);
- circular-origin alignment (issue #98);
- consensus quality/base-gap semantics (issues #50/#58);
- overlap admission (issue #85, fixed in Tracy in August 2026).

## Calibration gate

No relative quality, evidence weight, support ratio, consensus score, or
trace-mixture coefficient should be reported as Phred, probability, genotype
quality, or heteroplasmy fraction until empirical calibration supports that
interpretation.

Calibration evaluation should report reliability/calibration curves and
task-appropriate error metrics, not only correlation with Tracy.
