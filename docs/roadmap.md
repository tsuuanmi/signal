# Signal Roadmap

## Active objective

The current goal is **not** to maximize feature count.

Signal first needs one small, trustworthy Sanger analysis path whose behavior is scientifically understandable, deterministic, and validated on approved real traces.

The active MVP is:

```text
AB1
 ↓
validated chromatogram decode
 ↓
primary base calling
 ↓
basic read quality / end trimming
 ↓
forward-or-reverse alignment to one short reference
 ↓
simple primary-sequence SNV detection
 ↓
versioned JSON result
```

See [ADR-0021](adr/0021-freeze-scientific-core-mvp.md).

## MVP acceptance priorities

### 1. Decode the chromatogram correctly

Before improving variant logic, prove that Signal reads the relevant ABIF structures correctly:

- analyzed A/C/G/T channels;
- FWO channel ordering;
- PLOC loci;
- optional vendor evidence where documented;
- malformed and inconsistent input rejection.

The decoded signal is the evidence foundation. Every later stage depends on it.

### 2. Base-call correctly enough to trust the read

The first scientific target is a conservative primary sequence plus explicit ambiguity.

The basecaller must:

- derive calls from signal, not silently inherit vendor PBAS;
- retain enough signal evidence to explain a call;
- preserve unresolved states instead of guessing;
- behave deterministically at ties and thresholds.

Validation should compare against approved traces and independently established expected sequence, not only synthetic fixtures.

### 3. Trim only what can be justified

End trimming should remain simple and deterministic.

Current relative quality is not Phred-calibrated. MVP acceptance therefore requires evidence that trimming removes obviously poor tails without silently deleting trustworthy internal sequence.

More sophisticated confidence calibration is deferred.

### 4. Align the read correctly

For one short reference, Signal must:

- evaluate both orientations;
- select deterministically;
- preserve mapping back to original call indexes/PLOC;
- fail explicitly when placement is genuinely ambiguous.

Alignment correctness is more important than adding search/indexing features.

### 5. Call simple SNVs correctly

The first variant target is straightforward primary-sequence A/C/G/T substitutions.

MVP validation should answer:

- was the read placed correctly?
- does the mapped trace call support the alternate base?
- is the reference coordinate correct?
- is the allele reported on the reference strand?
- are unresolved calls excluded rather than guessed?

### 6. Keep output clear and stable

The JSON result should be easy to inspect and hard to misinterpret.

The schema should make explicit:

- input/config/reference identity;
- read and trim summary;
- alignment orientation and mapped region;
- simple variants and their supporting trace calls;
- warnings;
- coordinate conventions.

Schema stability and interpretability are more important than exposing every internal feature.

## Implemented but not required for core MVP acceptance

The repository already contains or explores functionality beyond this baseline, including:

- rolling SNR annotations;
- circular-reference handling;
- insertion/deletion extraction and normalization;
- batch orchestration;
- richer per-call evidence.

These may remain implemented and tested, but their existence does not expand the definition of the active MVP.

A capability becomes part of the release-critical scientific contract only after its own biological validation is strong enough.

## Deferred until after MVP confidence

The following are intentionally deferred:

1. insertion/deletion calling as a release-critical capability;
2. homopolymer and mtDNA poly-C special handling;
3. sample-level multi-read consensus;
4. bidirectional sample evidence aggregation;
5. quantitative heteroplasmy;
6. mixed-template or length-mixture decomposition;
7. haplogroup-based QC or inference;
8. calibrated quality/error probabilities;
9. ML-based calling, correction, or training export;
10. SCF, VCF/BCF, multi-contig references, and genome-scale indexing.

Research notes may continue to exist in `TODO.md`, `UPDATE.md`, and `tracy_review.md`, but they are not active delivery commitments.

## Validation before expansion

Before promoting harder features, complete an approved real-trace regression baseline for the core path.

For each approved trace, retain:

- AB1 checksum;
- source/instrument context when available;
- primer or expected region;
- orientation;
- reference checksum;
- exact configuration;
- expected primary sequence or independently established truth;
- expected simple SNVs;
- explanation of disagreements;
- runtime and peak memory.

The first milestone is not "Signal supports everything Tracy supports".

The first milestone is:

> Signal can take an ordinary Sanger AB1, produce a trustworthy primary read, align it correctly, report straightforward SNVs correctly, and explain the result through a stable schema.
