# Tracy Ideas Ranked by ROI

This is the compact prioritization layer. Detailed rationale lives in the focused research documents linked from [`README.md`](README.md).

This ranking is relative to Signal's current scope: deterministic Sanger AB1
processing for short references, with basecalling, alignment, and conservative
variant reporting already implemented.

ROI here combines:

- expected biological correctness or review value;
- amount of existing Signal evidence that can be reused;
- implementation and validation cost;
- architectural disruption;
- risk of introducing unsupported biological claims.

## Ranking

| Rank | Tracy idea | ROI | Signal interpretation |
|---|---|---|---|
| 1 | Use secondary/mixed signal in variant eligibility | Very high | Prevent a strongest-base difference from being treated as an ordinary clean SNV when the same locus carries meaningful competing signal. |
| 2 | Trace-profile-aware alignment | Very high | Align nucleotide evidence rather than only the collapsed primary sequence. This is Tracy's strongest architectural lesson for Signal. |
| 3 | Forward/reverse trace consensus | High | Reconcile independent evidence from both strands and reduce strand-specific artifacts. |
| 4 | Reference-guided multi-trace consensus | High, post-MVP | Combine overlapping reads in reference coordinates for sample-level mtDNA reconstruction. |
| 5 | Explicit review/evidence artifact | Medium-high | Make aligned call/signal evidence easy to inspect without bloating the compact production result. |
| 6 | Detect persistent mixed-signal/post-indel shifts | Medium-high research | Identify a transition from clean to systematically mixed trace without immediately assigning genotype or heteroplasmy. |
| 7 | Wild-type AB1 profile comparison | Medium | Useful for assay/control workflows, but less central than FASTA/rCRS comparison for the current mtDNA use case. |
| 8 | VCF/BCF projection | Medium | Useful interoperability output after the JSON contract is stable; should remain derived rather than authoritative. |
| 9 | Two-allele decomposition | Low now | Technically interesting, but Tracy's diploid interpretation does not map directly to mtDNA heteroplasmy. |
| 10 | Genome FM-index/search | Very low | Signal's short-reference use case does not justify the extra complexity yet. |
| 11 | De novo chromatogram assembly | Very low | Reference-guided coordinate reconciliation is simpler and more auditable for mtDNA. |
| 12 | SCF/FASTQ convenience output | Very low | Does not materially improve current biological correctness; FASTQ would also imply quality semantics Signal has not calibrated. |

## 1. Mixed evidence in simple-variant eligibility

### Why it is first

Signal already computes both a strongest primary base and an ambiguity/IUPAC
interpretation. The current variant path is intentionally based on the primary
sequence, so a mixed locus can still contribute its strongest base to a
primary-sequence difference.

For an MVP that wants trustworthy "easy variants" first, a clean substitution
and a mixed locus should not be treated as equivalent evidence.

Example:

```text
reference: A
signal:    A=430, G=510
primary:   G
ambiguity: R
```

This supports "mixed A/G evidence" more directly than "clean A>G SNV".

A conservative first step is to make mixed supporting calls ineligible for the
simple-variant path, with an explicit exclusion reason, while preserving the
evidence for later research.

### Why this is cheap

The required evidence already exists in `BaseCall`. No new signal algorithm is
required. The change would mainly affect variant eligibility, result warnings,
tests, and documentation.

## 2. Trace-profile-aware alignment

Tracy's important distinction is profile-to-sequence/profile-to-profile
alignment. A locus can remain something like:

```text
A 0.05
C 0.04
G 0.87
T 0.04
```

rather than becoming only `G`.

Signal should not copy Tracy's profile formula blindly. Signal already has
stronger local evidence primitives available:

- selected per-channel peaks;
- co-located signal at the primary event;
- local baseline estimates;
- first-difference MAD noise;
- local per-channel SNR observations;
- ambiguity membership;
- original call and PLOC coordinates.

A Signal-specific evidence profile can therefore be defined from explicit,
validated inputs and fed to a generalized Gotoh substitution score.

## 3. Forward/reverse consensus

Tracy demonstrates that two chromatograms from opposite strands can be compared
as profiles rather than reduced to a simple base vote.

For Signal, this should be a layer above the current one-trace pipeline:

```text
trace F -> single-trace analysis --+
                                   +-> reconciliation -> sample evidence
trace R -> single-trace analysis --+
```

The current invariant "one trace per core invocation" can remain intact.

## 4. Reference-guided multi-trace consensus

For tiled mtDNA reads, reference coordinates provide the natural common frame.
The first implementation should be reference-guided, not de novo:

```text
trace 1 --+
trace 2 --+-> independent placement on reference -> overlap reconciliation
trace N --+
```

This avoids introducing an assembly graph before there is a demonstrated need.

## 5. Review/evidence output

Tracy's UI-oriented outputs preserve enough trace/alignment context to inspect a
call. Signal already has the essential mapping primitives: call index, PLOC,
orientation-aware reference mapping, ambiguity, selected peaks, and quality
evidence.

A future review artifact should be independently versioned and opt-in. It should
not expand the compact production analysis schema with bulk arrays by default.

## 6. Persistent mixed-signal detection

Tracy's indel decomposition contains a useful lower-level idea: after a
heterogeneous indel, a trace can transition from mostly clean peaks to
systematically mixed signal.

Signal can use that phenomenon without adopting the biological conclusion. A
future detector may report:

```text
clean evidence -> transition -> persistent mixed evidence
```

with a breakpoint/confidence measure and an explicit `unresolved`
classification.

## Ideas intentionally deferred

### Genotype and allele-fraction semantics

A secondary peak in mtDNA can reflect heteroplasmy, noise, pull-up,
co-amplification, NUMTs, poor peak separation, or a mixed-length template.
Signal should not map Tracy's diploid genotype model directly onto these cases.

### Genome indexing

Tracy needs indexed search because it supports large genomes. Signal currently
uses one reference record capped at 50 kb and a bounded dynamic-programming
alignment. Until the reference scope changes, FM indexing has poor ROI.

### De novo assembly

For the intended mtDNA workflow, reference-guided overlap reconciliation has
clearer coordinates, fewer failure modes, and better auditability.
