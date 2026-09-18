# Tracy Research Validation Strategy

Tracy is a design and benchmark reference, not biological ground truth.

## 67. Validation Strategy

None of the Tracy-inspired improvements should be considered complete using only synthetic unit tests.

Validation should progress through several levels.

---

## 68. Level 1: Synthetic Unit Tests

Useful for:

```text
peak localization

co-localization

profile normalization

orientation

profile scoring

tie behavior

phase-shift candidate search
```

Examples should isolate one property at a time.

---

## 69. Level 2: Synthetic Chromatogram Shapes

Generate signal arrays containing:

```text
clean single peaks

double peaks

offset neighboring peaks

compressed spacing

baseline drift

saturation

low amplitude

phase shift after insertion

phase shift after deletion
```

This is useful before real biological data is available.

---

## 70. Level 3: Provenanced Real AB1 Corpus

Critical cases:

```text
clean homoplasmic-like mtDNA reads

forward/reverse pairs

poly-C regions

known indels

poor-quality reads

known mixed traces

amplicon overlaps
```

Each file should have:

```text
source

sample identity

assay context

truth status

expected region

direction

reference
```

---

## 71. Level 4: Independent Truth

For claims beyond basic primary-sequence differences, use independent truth where possible.

Examples:

```text
NGS

clonal sequencing

synthetic mixtures

validated reference materials
```

A second call from the same Sanger trace is not independent truth.

---

## 72. Benchmark Against Current Signal

Every new stage should compare against current Signal.

Metrics:

```text
alignment success rate

orientation accuracy

call retention

false ambiguity rate

variant concordance

indel concordance

manual-review burden
```

The new system should not silently degrade clean-read performance.

---

## 73. Benchmark Against Tracy

Tracy can also serve as a reference comparator.

Useful comparison categories:

```text
basecalls

ambiguity calls

trim bounds

orientation

alignment

consensus

mixed-indel candidates
```

The goal is not byte-for-byte compatibility.

The goal is:

```text
understand differences
```

and ensure deviations are intentional.

---
