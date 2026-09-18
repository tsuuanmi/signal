# Overview and Current Overlap

## 1. Executive Summary

Signal and Tracy overlap significantly in their low-level Sanger-processing foundations.

Signal already implements equivalents of several important Tracy concepts:

* ABIF/AB1 decoding;
* analyzed A/C/G/T channel extraction;
* PLOC-defined call windows;
* per-channel local peak search;
* strongest-primary calling;
* secondary-peak ratio handling;
* IUPAC ambiguity representation;
* peak-spacing and ambiguity-based quality heuristics;
* adaptive end trimming;
* affine-gap Gotoh alignment;
* forward/reverse orientation selection;
* SNV and small-indel extraction.

Therefore, Signal should **not** spend effort reimplementing Tracy's basic basecaller.

The most important lessons from Tracy are instead higher-level:

1. **Do not collapse the chromatogram to one primary nucleotide too early.**
2. **Represent every locus as an evidence profile that alignment and consensus can consume directly.**
3. **Use profile-to-profile comparison for forward/reverse read agreement.**
4. **Build sample-level consensus from signal evidence rather than primary-call voting.**
5. **Detect persistent post-indel phase shifts using change-point-like signal behavior.**
6. **Evaluate multiple candidate insertion/deletion shifts rather than trusting one alignment gap.**
7. **Filter or downgrade reads before they influence a sample consensus.**
8. **Use Tracy's mixed-indel decomposition as inspiration, but never directly inherit its diploid/heterozygous semantics for mtDNA.**

The recommended architectural direction is:

```text
AB1
 |
 v
ABIF decode
 |
 v
signal-derived peak candidates
 |
 v
locus refinement
 |
 v
LocusEvidence
 |
 +----------------------+----------------------+
 |                      |                      |
 v                      v                      v
primary call      EvidenceProfile       mixed-signal analysis
 |                      |                      |
 |                      v                      |
 |               profile alignment            |
 |                      |                      |
 +----------------------+----------------------+
                        |
                        v
                  ReadObservation
                        |
               +--------+--------+
               |                 |
               v                 v
          forward reads      reverse reads
               |                 |
               +--------+--------+
                        |
                        v
               evidence consensus
                        |
                        v
                 sample-level mtDNA
                        |
         +--------------+---------------+
         |              |               |
         v              v               v
      variants      mixed sites      sample QC
```

The central design principle is:

> **Primary sequence should remain one interpretation of the chromatogram, not the only representation of the chromatogram.**

---

## 2. Scope of This Document

This document focuses on lessons from Tracy that are relevant to Signal's future development.

Primary goals:

* improve signal representation;
* improve alignment robustness;
* improve forward/reverse read reconciliation;
* support multiple reads from one biological sample;
* improve mtDNA indel handling;
* detect mixed-length signal patterns;
* preserve conservative biological semantics;
* retain Signal's deterministic and auditable design.

This document does **not** recommend adopting Tracy wholesale.

Specifically, it does not recommend prioritizing:

* genome-scale FM indexing;
* de novo chromatogram assembly;
* Tracy's diploid heterozygous interpretation;
* unvalidated allelic-fraction estimation;
* SCF support;
* FASTQ output;
* VCF/BCF output;
* Phred-like quality labels without empirical calibration.

---

## 3. Relevant Tracy Architecture

Tracy supports several operations:

```text
chromatogram
    |
    +--> basecalling
    |
    +--> alignment
    |
    +--> decomposition
    |
    +--> consensus
    |
    +--> assembly
    |
    +--> variant calling
```

Relevant source areas include:

```text
src/abif.h
src/profile.h
src/align.h
src/gotoh.h
src/trim.h
src/consensus.h
src/decompose.h
src/assemble.h
```

The strongest lesson is not any individual function.

The important design pattern is:

```text
raw chromatogram
      |
      v
basecall information
      |
      v
continuous nucleotide profile
      |
      v
alignment / comparison / consensus
```

Signal currently performs much of its downstream analysis after reducing the chromatogram to a conservative primary sequence.

That is appropriate for the current MVP, but eventually becomes limiting.

---

## 4. What Signal Already Implements

Before introducing new features, it is important to recognize which Tracy ideas are already present.

### 4.1 Midpoint-Based Call Windows

Signal constructs call windows around PLOC loci using neighboring call positions.

Conceptually:

```text
PLOC[i-1]       PLOC[i]        PLOC[i+1]
     |             |               |
     +------|------+-------|-------+
            ^              ^
        midpoint        midpoint
```

This is already a sensible approach.

There is no strong reason to replace it with Tracy's implementation.

---

### 4.2 Per-Channel Local Peak Search

Signal already searches each A/C/G/T channel independently inside a locus window.

For every channel:

```text
find strongest positive local maximum
```

and if no suitable local maximum exists:

```text
fallback to signal value at PLOC
```

This is conceptually close to Tracy.

No major rewrite is justified solely for Tracy compatibility.

---

### 4.3 Secondary-Peak Ratio

Signal already supports:

```toml
secondary_peak_ratio = 0.33
```

which is also conceptually similar to Tracy's default peak ratio.

In `signal.peak_recall/v3`, this threshold requires both a sufficiently strong selected channel peak and sufficiently strong channel signal at the uniquely strongest primary peak sample. This rejects a remote channel maximum elsewhere in the same PLOC window without claiming that the initial sample-based gate is a complete peak-geometry model.

---

### 4.4 Primary and Ambiguity Calls

Signal already separates:

```text
primary
```

from:

```text
ambiguity
```

Example:

```text
A dominant
G sufficiently strong
```

may produce:

```text
primary   = A
ambiguity = R
```

This is a strong design decision and should be preserved.

---

### 4.5 Relative Quality and End Trimming

Signal already implements a Tracy-like concept of read quality based on:

* local ambiguity;
* call spacing consistency;
* a best section;
* outward trimming.

Signal additionally documents that this score is:

```text
relative_quality
```

and not:

```text
Phred
```

This distinction is important and should remain explicit.

---

### 4.6 Affine-Gap Alignment

Signal already has a deterministic Gotoh implementation with:

* match score;
* mismatch score;
* ambiguous-base score;
* gap-open score;
* gap-extension score;
* semi-global behavior;
* forward/reverse orientation handling;
* circular-reference support.

There is no need to port Tracy's Gotoh implementation.

Future changes should extend the *scoring input*, not replace the core dynamic-programming framework unless benchmarks demonstrate a need.

---
