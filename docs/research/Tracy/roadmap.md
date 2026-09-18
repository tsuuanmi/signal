# Tracy Research Roadmap

This roadmap is a sequencing of research and validation work, not a commitment to ship every phase.

## 74. Suggested Development Order

### Phase A — Peak evidence foundation

Implement:

```text
baseline

corrected height

prominence

local noise

per-channel SNR

spacing-aware co-localization beyond the v3 gate

locus refinement
```

Output:

```text
LocusEvidence
```

Do this first.

---

## 75. Phase B — Evidence profile

Implement:

```text
LocusEvidence
    ->
EvidenceProfile
```

Initially keep:

```text
primary calling unchanged
```

to isolate profile behavior from basecalling behavior.

---

## 76. Phase C — Profile/reference alignment

Add optional:

```text
profile-aware substitution scoring
```

while retaining:

```text
primary-sequence Gotoh
```

as comparison mode.

Benchmark both.

---

## 77. Phase D — ReadObservation

Map each accepted read into:

```text
reference-coordinate observations
```

This becomes the stable sample-analysis input.

---

## 78. Phase E — Two-read consensus

Start with the simplest high-value case:

```text
one forward AB1
+
one reverse AB1
```

Implement:

```text
profile/profile consistency

bidirectional support

discordance

consensus
```

before general N-read assembly.

---

## 79. Phase F — Multi-read sample consensus

Add:

```text
manifest

read admission

multiple amplicons

coverage map

sample consensus

sample variants
```

---

## 80. Phase G — Length-mixture detection

Implement:

```text
signal-cleanliness metric

change-point search

candidate ±N phase shifts

evidence ranking
```

Initially report only:

```text
length_mixture_candidate
```

---

## 81. Phase H — mtDNA-specific interpretation

Add:

```text
poly-C context

repeat context

mtDNA nomenclature projection

haplogroup consistency QC
```

These should remain downstream of generic signal and alignment stages.

---

## 82. Phase I — Calibration

Only after sufficient data:

```text
calibrated call confidence

validated mixed-base detection

validated heteroplasmy estimation
```

---

## 83. ROI Ranking

Recommended priority:

| Priority       | Improvement                             |     Expected ROI |      Effort |
| -------------- | --------------------------------------- | ---------------: | ----------: |
| P0             | Peak geometry beyond the v3 sample gate |        Very high |      Medium |
| P0             | Rich `LocusEvidence`                    |        Very high |      Medium |
| P0             | Evidence profiles                       |        Very high |      Medium |
| P0             | Profile-to-reference alignment          |        Very high |      Medium |
| P0             | Forward/reverse profile consensus       |        Very high | Medium–High |
| P1             | Read admission / sample QC              |             High |  Low–Medium |
| P1             | Sample-level consensus                  |        Very high | Medium–High |
| P1             | Change-point length-mixture detection   |        Very high |      Medium |
| P1             | Candidate ±N phase-shift evaluation     |        Very high |      Medium |
| P1             | Poly-C/repeat context                   |             High |      Medium |
| P2             | Multi-amplicon whole-mtGenome consensus |             High |        High |
| P2             | Alignment-stability evidence            |      Medium–High |      Medium |
| P2             | mtDNA nomenclature layer                |           Medium |      Medium |
| P3             | VCF export                              |       Low–Medium |         Low |
| P3             | FASTQ export                            |              Low |         Low |
| P3             | SCF support                             |              Low |      Medium |
| Skip for mtDNA | FM-index genome alignment               |         Very low |        High |
| Defer          | Quantitative heteroplasmy               | Potentially high |   Very high |

---

## 84. Two Highest-Value Tracy Lessons

If Signal only adopts two major concepts from Tracy, they should be:

### 84.1 Keep nucleotide evidence through alignment

Instead of:

```text
chromatogram
    ->
primary sequence
    ->
alignment
```

move toward:

```text
chromatogram
    ->
LocusEvidence
    ->
EvidenceProfile
    ->
alignment
```

This preserves information Signal already extracts but currently discards from alignment semantics.

---

### 84.2 Model persistent post-indel phase shifts

Instead of treating every indel as:

```text
one gap in one alignment
```

also ask:

```text
Does an insertion/deletion shift explain a persistent change in the downstream chromatogram?
```

This is particularly valuable for:

```text
poly-C regions

homopolymers

length-mixture candidates

mixed mtDNA traces
```

Tracy provides useful algorithmic inspiration for both breakpoint detection and candidate shift testing.

---
