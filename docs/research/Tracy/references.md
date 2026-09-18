# Tracy Source Reference Map

## 88. Tracy Source Areas Worth Keeping as References

When implementing future work, the following Tracy files are particularly useful as conceptual references.

### Basecalling and signal interpretation

```text
src/abif.h
```

Useful for:

```text
peak selection
primary/secondary handling
quality heuristics
```

---

### Trace profiles

```text
src/profile.h
```

Useful for:

```text
representing nucleotide signal as a profile
profile reverse complement
trace/reference profile construction
```

---

### Profile-aware alignment

```text
src/align.h
src/gotoh.h
```

Useful for:

```text
profile-to-sequence scoring
profile-to-profile scoring
affine-gap DP integration
```

Signal should keep its own Gotoh implementation and borrow only the profile-scoring concept.

---

### Forward/reverse consensus

```text
src/consensus.h
```

Useful for:

```text
orientation selection

profile-to-profile alignment

combining evidence

pairwise consensus
```

Avoid directly importing Tracy's quality/genotype terminology.

---

### Mixed-indel decomposition

```text
src/decompose.h
```

Useful for:

```text
change-point-like breakpoint detection

persistent phase-shift detection

candidate insertion/deletion shift evaluation

robust candidate comparison
```

Do not inherit diploid heterozygous assumptions.

---

### Multi-trace assembly

```text
src/assemble.h
```

Useful for:

```text
read admission

orientation handling

multi-read workflow

consensus construction
```

Signal should prefer reference-coordinate mtDNA consensus over directly porting Tracy's progressive assembly.

---

## 89. Decision Summary

Recommended:

```text
YES  LocusEvidence
YES  peak co-localization
YES  locus refinement
YES  evidence profiles
YES  profile/reference alignment
YES  profile/profile comparison
YES  F/R evidence consensus
YES  sample-level read model
YES  read admission
YES  phase-shift change-point detection
YES  candidate ±N shift testing
YES  repeat/poly-C context
YES  multi-amplicon reference-coordinate consensus
```

Defer:

```text
heteroplasmy quantification

calibrated Phred-like confidence

haplogroup-based interpretation
```

Low priority:

```text
SCF

FASTQ

VCF/BCF
```

Avoid for mtDNA-specific core:

```text
FM-index genome search

direct Tracy de novo assembly port

direct diploid decomposition semantics

raw signal ratio = heteroplasmy percentage
```

---

## 90. Closing Principle

The strongest lesson from Tracy can be summarized in one sentence:

> **A Sanger chromatogram contains richer nucleotide evidence than the final primary base string, and Signal should preserve that evidence for as long as possible.**

For mtDNA, the corresponding sample-level principle is:

> **Independent forward, reverse, replicate, and overlapping-amplicon observations should be combined as evidence, not merely as called strings.**

Those two principles should guide the next major architectural evolution of Signal.

## Source-to-Signal map

| Tracy source area | Research lesson | Signal research document |
|---|---|---|
| `src/abif.h`, `src/trim.h` | basecall evidence, relative quality, trimming | `overview.md`, `features/locus-evidence.md` |
| `src/profile.h` | keep nucleotide evidence as profiles | `features/evidence-profiles.md` |
| `src/gotoh.h`, `src/align.h` | profile-aware substitution scoring | `features/profile-alignment.md` |
| `src/consensus.h` | profile-to-profile reconciliation | `features/sample-analysis.md` |
| `src/decompose.h` | persistent phase/mixed-signal changes | `features/mixed-signal-indels.md` |
| `src/assemble.h`, `src/msa.h` | multi-read overlap and consensus | `features/multi-amplicon-consensus.md` |
