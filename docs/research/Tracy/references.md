# Tracy Source Reference Map

## Audit baseline

The current source audit is pinned to Tracy commit:

```text
0672fb096b98c4fd36da47d634c8b89cd86cb217
2026-09-10
```

The primary publication is:

> Rausch T, Fritz MH, Untergasser A, Benes V. Tracy: basecalling, alignment,
> assembly and deconvolution of sanger chromatogram trace files. BMC Genomics
> 21, 230 (2020).

Paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC7071639/

Detailed findings from the pinned source revision and public issue history live
in [`source-audit.md`](source-audit.md).

## Source areas worth keeping as references

### Basecalling and signal interpretation

```text
src/abif.h
src/trim.h
```

Useful for peak windows, primary/secondary handling, quality heuristics, and
trimming. Do not copy the basecall-gated profile semantics or treat the heuristic
quality as calibrated.

### Trace profiles

```text
src/profile.h
```

Useful for profile reverse complement and the general idea that trace evidence
can survive past a primary string. Signal should construct profiles from its own
channel evidence rather than from thresholded call membership.

### Profile-aware alignment

```text
src/align.h
src/gotoh.h
```

Useful for expected match/mismatch profile scoring and integration with affine
DP. Signal should retain its own Gotoh implementation, explicit tie ordering,
circular topology, and deterministic numeric policy.

### Pairwise consensus

```text
src/consensus.h
```

Useful for profile/profile orientation and overlap admission. Avoid importing
uncalibrated likelihood/quality terminology or assuming gap evidence is
equivalent to nucleotide evidence.

### Progressive multi-trace alignment

```text
src/msa.h
src/assemble.h
```

Useful for orientation search, progressive profile alignment, guide-tree ideas,
and reference-guided read admission. Final Tracy assembly consensus is a
quality-blind character majority vote, so that part should not be copied.

### Mixed-indel decomposition

```text
src/decompose.h
src/indigo.h
```

Useful for change-point-like breakpoint detection and candidate ±N shift
evaluation. Signal should not reuse reference-threading that mutates observed
basecalls, diploid semantics, or uncalibrated allele-fraction estimation.

### Reference search and placement

~~~text
src/fmindex.h
src/fasta.h
src/sage.h
~~~

Useful for understanding seed-and-extend architecture, reference slicing,
orientation search, and the sensitivity tradeoff between exact k-mer anchoring
and direct profile alignment. Signal should keep candidate search separate from
authoritative alignment and preserve circular topology.

### Variant projection and optional annotation

~~~text
src/variants.h
src/web.h
~~~

`variants.h` is useful for coordinate provenance and interchange projection.
`web.h` demonstrates downstream known-variant annotation but should not be part
of Signal's deterministic core.

Useful for preserving links among reference position, basecall position, raw
signal position, and method identity. Genotype/GQ semantics are coupled to
Tracy's decomposition and heuristic qualities and are not directly portable.

## Public issues that expose useful failure modes

| Issue | Finding | Signal lesson |
|---|---|---|
| [#15](https://github.com/gear-genomics/tracy/issues/15) / [#34](https://github.com/gear-genomics/tracy/issues/34) | exact k-mer anchoring is less sensitive than direct profile alignment | separate candidate search from authoritative alignment |
| [#41](https://github.com/gear-genomics/tracy/issues/41) | indexed/unindexed paths fail at circular origin | topology belongs in placement as well as alignment |
| [#50](https://github.com/gear-genomics/tracy/issues/50) | assembly quality is support-fraction based rather than per-base calibrated quality | do not label consensus support as Phred without calibration |
| [#58](https://github.com/gear-genomics/tracy/issues/58) | assembly is majority vote; base-vs-gap conflicts are not quality-symmetric | model gap/indel support explicitly |
| [#79](https://github.com/gear-genomics/tracy/issues/79) | local FASTA can rescue placement but loses genome-coordinate context for annotation | local slices require parent-coordinate mapping |
| [#85](https://github.com/gear-genomics/tracy/issues/85) | pairwise consensus needed explicit overlap/agreement controls; implemented 2026-08-18 | read admission belongs before consensus |
| [#91](https://github.com/gear-genomics/tracy/issues/91) | Tracy requires original machine peak locations | make PLOC dependency/completeness explicit |
| [#98](https://github.com/gear-genomics/tracy/issues/98) | Tracy aligns to linear references only | preserve Signal's explicit circular topology |
| [#116](https://github.com/gear-genomics/tracy/issues/116) | high-amplitude dye-blob artifacts are unsupported | validate local artifact resilience before profile promotion |

## Source-to-Signal map

| Tracy source area | Research lesson | Signal research document |
|---|---|---|
| `src/abif.h`, `src/trim.h` | event anchors, peak selection, relative quality, trimming | `overview.md`, `source-audit.md`, `features/locus-evidence.md` |
| `src/profile.h` | preserve nucleotide evidence but avoid basecall-gated profiles | `source-audit.md`, `features/evidence-profiles.md` |
| `src/gotoh.h`, `src/align.h` | profile scoring with explicit numeric/tie semantics | `source-audit.md`, `features/profile-alignment.md` |
| `src/consensus.h` | pairwise profile reconciliation and overlap admission | `source-audit.md`, `features/sample-analysis.md` |
| `src/decompose.h`, `src/indigo.h` | persistent phase changes; avoid reference mutation/diploid semantics | `source-audit.md`, `features/mixed-signal-indels.md` |
| `src/assemble.h`, `src/msa.h` | multi-read layout; avoid quality-blind majority consensus | `source-audit.md`, `features/multi-amplicon-consensus.md` |
| `src/fmindex.h`, `src/fasta.h`, `src/sage.h` | candidate search vs authoritative alignment; reference slicing | `source-audit.md`, `features/reference-placement.md`, `deferred.md` |
| `src/variants.h`, `src/web.h` | coordinate provenance and downstream annotation | `source-audit.md`, `deferred.md` |

## Decision summary

Recommended:

```text
YES  explicit PLOC evidence state
YES  artifact observations / local robust evidence
YES  LocusEvidence
YES  peak co-localization
YES  locus refinement
YES  basecall-independent evidence profiles
YES  profile/reference alignment
YES  profile/profile comparison
YES  explicit overlap/read admission
YES  evidence- and gap-aware F/R consensus
YES  immutable sample-level observations
YES  phase-shift change-point detection
YES  candidate ±N shift testing
YES  repeat/poly-C context
YES  multi-amplicon reference-coordinate consensus
YES  explicit candidate-placement/final-alignment boundary if scaling beyond short references
YES  reference guidance separated from observed sample support
```

Defer:

```text
heteroplasmy quantification
calibrated Phred-like confidence
haplogroup-based interpretation
```

Avoid as direct ports:

```text
FM-index genome search for current mtDNA scope
reference-as-an-extra-read consensus semantics
network annotation inside the deterministic core
quality-blind majority consensus
reference mutation of observed basecalls
direct diploid decomposition semantics
raw signal reconstruction coefficient = heteroplasmy percentage
```
