# Deferred or Low-ROI Tracy Features

## 56. Features From Tracy That Should Not Be Prioritized

### 56.1 FM Index / large-reference seed search

Tracy's FM-index is useful mainly because direct profile dynamic programming
does not scale to large genomes. Its architecture is worth remembering:

~~~text
exact k-mer candidate search
    ->
local reference slice
    ->
profile-to-sequence refinement
~~~

The public issue history also documents the cost: exact anchoring is less
sensitive with Ns, incorrect primary calls, repeats, and short usable sequence.

Signal's current mtDNA/short-reference scope does not need this complexity.
Prefer the existing bounded circular affine-gap alignment, and consider banding
before genome indexing if performance becomes a problem.

If Signal later expands to genome-scale references, candidate search can be
added as a separate acceleration stage under ADR-0012. It must not become the
authoritative scientific alignment.

---

## 57. De Novo Assembly

Tracy can perform de novo chromatogram assembly.

For mtDNA, Signal usually knows:

```text
reference = rCRS
```

and often:

```text
expected amplicon
primer
direction
```

Reference-guided placement is simpler and safer.

De novo assembly is therefore low priority.

---

## 58. SCF Input

SCF support may be useful eventually, but it does not significantly improve core mtDNA analysis.

Priority should remain:

```text
AB1 quality
consensus
mixed-signal evidence
indel handling
```

before broadening input formats.

---

## 59. FASTQ Output

Signal currently uses structured JSON as the scientific contract.

FASTQ could eventually be exported from:

```text
primary sequence
+
calibrated quality
```

but until quality is calibrated, FASTQ may imply semantics Signal does not actually support.

Low priority.

---

## 60. VCF/BCF Output

VCF export can be useful for interoperability.

However, it should remain an adapter:

```text
Signal canonical variants
      |
      v
VCF projection
```

rather than making VCF the internal scientific model.

For mtDNA-specific notation, a separate representation layer may be preferable.

---

## 61. Tracy Allelic Fraction

Tracy contains code for estimating allelic proportions from trace signal.

This should **not** be ported directly.

Reasons:

* designed around two-allele assumptions;
* not mtDNA-specific;
* raw channel proportions are not necessarily calibrated mixture fractions;
* sequencing chemistry and base context affect signal amplitude;
* forward and reverse reads may have different response curves.

Signal may study it as a feature-engineering reference only.

---
