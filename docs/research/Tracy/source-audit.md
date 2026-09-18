# Tracy Source Audit

This audit records concrete behavior observed in Tracy source code and public issue
history, then translates it into lessons for Signal. It complements the
feature-oriented research notes with implementation-level facts.

- Tracy source revision reviewed: `0672fb096b98c4fd36da47d634c8b89cd86cb217`
  (2026-09-10)
- Research date: 2026-09-18
- Primary paper: Rausch et al., *BMC Genomics* 21, 230 (2020)
- Scope: `abif.h`, `profile.h`, `align.h`, `gotoh.h`, `consensus.h`,
  `msa.h`, `assemble.h`, `decompose.h`, `indigo.h`, `variants.h`,
  plus relevant public issues.

This document is descriptive of Tracy and prescriptive only for the research
requirements explicitly promoted into this directory's SRS/ADRs.

## 1. Basecalling depends on instrument peak positions

Tracy does not discover a new sequence of chromatogram events from the raw
waveform. Its basecaller uses the original machine-provided basecall positions
as anchors, builds midpoint windows around those positions, and searches each
A/C/G/T channel for a local maximum inside each window.

The practical consequence is visible in Tracy issue #91: a file may contain many
raw basecall characters but only a short PLOC/basecall-position series. Tracy's
maintainer confirmed that Tracy needs the peak locations and therefore stops
where those positions stop.

### Signal lesson

Signal currently also treats PLOC as required canonical input. That is a valid
MVP constraint, but it should be explicit as a scientific dependency rather than
an incidental parser detail.

Future work should distinguish:

```text
valid complete PLOC evidence
valid but suspicious/incomplete PLOC evidence
no usable PLOC evidence
```

A future PLOC-independent event detector would be a new basecalling method, not
a silent fallback inside the current method.

## 2. Tracy's peak ratio is local-window based, but still vulnerable to artifacts

For each PLOC-derived window Tracy:

1. finds the strongest local maximum independently in each channel;
2. estimates a threshold from the strongest channel value at the window
   midpoint;
3. falls back to midpoint channel values if all selected maxima are below that
   threshold;
4. normalizes selected channel maxima by the strongest selected peak;
5. admits channels above `pratio` (default 0.33).

This is local in window coordinates, but it is not a robust artifact model.

Issue #116 documents a current real-world limitation: high-amplitude dye blobs
can dominate the signal and cause Tracy to return unusable `N` calls. The
maintainer explicitly stated in August 2026 that Tracy cannot handle these
high-amplitude artifacts.

### Signal lesson

Signal should keep artifact handling separate from ordinary peak competition.
A high-amplitude outlier is not evidence that every lower-amplitude event is
biologically weak.

Before richer profile alignment is trusted, Signal should validate explicit
artifact observations such as:

- saturation or clipping;
- local amplitude outliers;
- dye-blob-like broad peaks;
- baseline shifts;
- neighboring-event interference.

Signal's current robust local SNR work is useful evidence, but it remains
observation-only and therefore does not by itself make the caller artifact
resilient.

## 3. Tracy profiles are basecall-gated, not raw four-channel distributions

Tracy's `createProfile` is an important architectural idea but its exact formula
should not be copied.

For each called locus Tracy computes:

```text
allBaseSig = A + C + G + T at bcPos

totalsig = sum of channels represented by primary or secondary call
normfac  = totalsig / allBaseSig
```

The called channels are normalized inside `totalsig`. The resulting A/C/G/T
profile is then softened toward a uniform vector:

```text
profile[k] =
    normfac * called_profile[k]
    + (1 - normfac) * 0.25
```

If `totalsig == 0`, Tracy uses `[0.25, 0.25, 0.25, 0.25]`.

The key detail is that the continuous-looking profile is downstream of the
discrete primary/secondary threshold decision. A channel excluded by the
basecaller does not retain its own measured relative evidence; its contribution
re-enters only indirectly through the uniform softening term.

### Signal lesson

A Signal evidence profile should be built from explicit channel evidence, not
from "which bases already passed an ambiguity threshold". Otherwise downstream
profile alignment cannot recover information already removed upstream.

Primary/ambiguity calls can be projections of the evidence profile, but they
should not be the gate that defines the profile.

## 4. Tracy profile scoring is an expected match/mismatch score with integer quantization

Tracy's profile-aware Gotoh code converts sequence/MSA inputs into six-row
profiles:

```text
A C G T N -
```

For profile-to-profile cells it computes an expected match/mismatch score over
rows A/C/G/T/N. The gap row is handled by the affine-gap DP rather than the
substitution calculation.

Conceptually:

```text
score(i,j) =
    sum_k1 sum_k2
        p1[k1,i] * p2[k2,j]
        * (match if k1 == k2 else mismatch)
```

The accumulated floating-point score is then cast to an integer before entering
the DP recurrence.

### Signal lesson

The scoring abstraction is worth learning from; the numeric policy is not.

Signal should define one explicit deterministic scoring representation, ideally
fixed-point or otherwise quantized by a documented rule before DP comparison.
That avoids platform-sensitive floating comparisons and makes tie behavior part
of the algorithm contract.

## 5. Tracy alignment tie behavior is deterministic but biologically arbitrary in places

Tracy uses explicit end-gap configurations for global, overlap/end-free, and
semi-global behavior. This is a useful separation.

In traceback, however, equality with a horizontal-gap score is checked before a
vertical-gap score, and both are checked before diagonal substitution. This
creates a deterministic but algorithm-specific preference among equal-scoring
placements.

Orientation selection also has explicit tie bias in several commands:

```cpp
if (forward_score > reverse_score) forward;
else reverse;
```

Therefore exact forward/reverse score ties select reverse.

### Signal lesson

Signal should continue treating tie ordering as an explicit invariant. Equal
score is not biological evidence for one orientation or indel placement. A tie
should either have a documented stable preference or remain an explicit
ambiguous state when the distinction matters scientifically.

## 6. Pairwise consensus is profile-aware, but its "likelihood" terminology is stronger than the evidence

`tracy consensus` aligns two trimmed trace profiles and combines overlapping
positions by adding the two six-state profile vectors.

It then:

1. normalizes the six combined weights;
2. takes `log10(weight)`;
3. labels these values "genotype likelihoods";
4. selects the best state;
5. optionally emits a two-base IUPAC code when the second-best canonical base
   has normalized weight greater than 0.1;
6. derives a quality from the top two normalized weights.

These values are useful ranking/evidence scores, but they are not derived from a
validated sequencing error model.

As of commit `086096586846d3ea3fd808e3252218b16e731def`
(2026-08-18), pairwise consensus additionally rejects alignments with less than
a configurable minimum overlap (default 25) or match fraction (default 0.5).
That change directly addressed long-standing user feedback in issue #85.

### Signal lesson

Two ideas are worth adopting:

- explicit overlap/read-admission gates before consensus;
- combining nucleotide evidence rather than selecting one primary call.

Do not call normalized evidence a probability, genotype likelihood, or Phred
quality without calibration.

## 7. Gaps are a separate evidence problem

Tracy's pairwise consensus can use evidence profiles for overlapping
nucleotides, but gaps do not have chromatogram quality in the same way a called
base does.

This limitation appears in issue #58. The maintainer explained that pairwise
consensus improved low-quality-vs-high-quality base handling, but low-quality
insertions versus gaps remained unresolved because the gap has no comparable
quality observation.

### Signal lesson

A future sample consensus needs a first-class model for insertion/deletion
support. It should not force a gap into the same scalar confidence abstraction
as a nucleotide.

Useful evidence can include:

- independent traces supporting the same gap placement;
- local profile/alignment stability;
- neighboring call spacing;
- retained quality around the event;
- alternate equally scoring gap placements;
- repeat/homopolymer context.

## 8. Multi-trace assembly uses profile alignment but character majority consensus

Tracy's multi-trace assembly has two sophisticated alignment modes:

- reference-guided progressive alignment;
- de novo progressive MSA using pairwise profile scores and a UPGMA-like guide
  tree.

This is a strong architectural reference for orientation, progressive overlap,
and profile-to-profile alignment.

However, final assembly consensus is simpler than the alignment machinery. The
MSA is converted to characters and each column is called by majority count over
A/C/G/T/gap. Per-trace base quality is not used.

The Tracy maintainer confirmed in issues #50 and #58 that:

- assembly quality is essentially a flat prior scaled by fraction of traces
  supporting the consensus base;
- `tracy assemble` is a simple majority vote;
- ties are arbitrary/deterministic rather than quality-aware;
- at least historically, nucleotide-versus-gap ties favored the nucleotide.

The current source also uses a global trace-count denominator for its FASTQ-like
consensus quality rather than a calibrated local error probability.

### Signal lesson

Profile-aware alignment should not be followed by evidence-destroying majority
vote.

Signal sample consensus should preserve per-observation evidence through the
final reconciliation step. Local coverage, admission state, strand, ambiguity,
and event type should remain available when deciding a sample locus.

## 9. Multi-trace coverage threshold has non-obvious integer behavior

Tracy assembly computes:

```text
covThreshold = int(fractionCalled * number_of_traces)
```

and separately requires observed coverage >= 1.

At the default `fractionCalled = 0.1`, fewer than ten traces yield a truncated
threshold of zero, so the effective minimum becomes one trace.

### Signal lesson

Coverage policy should be expressed directly in integer semantics, for example:

```text
minimum_observations
minimum_independent_strands
minimum_fraction_of_admitted_reads
```

If a fractional rule is used, rounding must be explicit and tested.

## 10. Tracy decomposition is reference-threading, not purely signal decomposition

Tracy's mixed-indel path first detects a potential phase transition using the
difference between the largest and second-largest profile weights.

For each possible breakpoint it compares two 25-base windows:

```text
left  = mean(best - second_best) before breakpoint
right = mean(best - second_best) after breakpoint
diff  = abs(right - left)
```

A best difference below 0.25 is treated as no mixed-indel shift.

For decomposition, Tracy then evaluates candidate insertion/deletion offsets by
counting downstream reference mismatches that cannot be explained by the
secondary call. A median/MAD-derived threshold and local-minimum heuristics
select candidate shifts.

The important architectural detail is that Tracy then uses
`phaseRefAllele` to rewrite `bc.primary` and `bc.secondary` according to the
reference threading hypothesis.

### Signal lesson

The change-point concept is useful. Mutating basecall evidence with a
reference-derived hypothesis is not appropriate for Signal's evidence-oriented
architecture.

Signal should preserve:

```text
observed call evidence
reference-aware interpretation
candidate phase-shift hypothesis
```

as separate immutable layers.

## 11. Tracy allele fractions are reconstruction coefficients, not mtDNA heteroplasmy estimates

After deriving two allele strings, Tracy samples normalized A/C/G/T signal at
positions where those strings differ. It then brute-forces mixture coefficients
for up to four constructed allele components in 0.01 steps and minimizes signal
reconstruction SSE.

This is reasonable for its intended gene-editing/diploid use case. It is not an
assay-calibrated mtDNA heteroplasmy fraction.

### Signal lesson

Do not reuse this estimator for mtDNA. A future heteroplasmy model needs
controlled mixtures, run/instrument stratification, false-positive analysis, and
an explicit limit of detection.

## 12. Tracy variant GT/GQ is coupled to decomposition heuristics

Tracy calls variants by separately aligning the two decomposed allele strings to
the reference. If the same variant is observed in both allele alignments, the
stored genotype counter is incremented and later emitted as homozygous; one
allele produces heterozygous output.

Variant QUAL/GQ comes from Tracy's estimated per-base quality heuristic, not a
calibrated genotype model.

The most reusable part of the BCF design is not GT/GQ. It is provenance:

- reference position;
- trace basecall position (`BASEPOS`);
- raw signal position (`SIGNALPOS`);
- method identity.

### Signal lesson

Signal already follows the stronger direction: keep precise call/PLOC/reference
mappings and avoid unsupported genotype claims. Any future interchange format
should project those authoritative typed mappings.

## 13. Circular references are a known Tracy limitation

Issue #98 confirms that Tracy aligns against linear references and does not
natively handle traces crossing a circular plasmid origin.

### Signal lesson

Signal's explicit circular topology and origin-crossing alignment are already a
meaningful architectural improvement over Tracy. This should remain a protected
regression area when evidence-profile alignment is introduced.

## 14. Research priorities updated by this audit

The source/issue audit changes the emphasis of the Tracy roadmap:

1. **Keep mixed supporting evidence out of the clean/simple variant path.**
2. **Add PLOC completeness and artifact-resilience validation before richer
   profiles make weak evidence look sophisticated.**
3. **Build evidence profiles directly from channel evidence, not from
   thresholded basecall membership.**
4. **Generalize the existing deterministic Gotoh scorer without importing
   Tracy's float-to-int scoring/tie semantics.**
5. **Make pairwise/sample consensus evidence-aware and explicitly gap-aware.**
6. **Use Tracy's mixed-indel breakpoint as an observation-only hypothesis
   generator; never rewrite observed basecall evidence from the reference.**
7. **Preserve Signal's circular-reference and variant-normalization strengths.**

## 15. Public issue references

- Tracy #50: "How are the base quality score generated?"
- Tracy #58: "Base quality and consensus generation"
- Tracy #85: consensus overlap controls; implemented in August 2026
- Tracy #91: dependency on original instrument peak locations
- Tracy #98: linear-reference limitation across circular origins
- Tracy #116: high-amplitude artifact / dye-blob limitation

The issue history is valuable because it exposes operational failure modes that
are not obvious from the paper alone.
