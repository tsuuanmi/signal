# Tracy-Informed Research Software Requirements Specification

## 1. Purpose

This SRS defines requirements for Tracy-inspired research inside Signal. It mirrors the role of the root Signal SRS but is not a production contract. A requirement here becomes normative only after promotion through the root ADR/SRS/schema process and implementation.

## 2. Scope boundary

- **TR-SRS-SCOPE-001:** Improve biological correctness, evidence preservation, reviewability, or a demonstrated engineering constraint; feature parity with Tracy is not a goal.
- **TR-SRS-SCOPE-002:** The current single-trace Signal pipeline remains the production baseline until a root-level decision changes it.
- **TR-SRS-SCOPE-003:** Tracy behavior is comparison evidence, not ground truth.
- **TR-SRS-SCOPE-004:** Research documents shall distinguish proposed behavior from implemented behavior.

## 3. Locus evidence

- **TR-SRS-EVID-001:** Richer locus evidence shall retain original call index, PLOC/sample coordinates, canonical A/C/G/T channel order, and method identity.
- **TR-SRS-EVID-002:** Secondary evidence shall be spatially compatible with the same nucleotide event; peak strength alone is insufficient.
- **TR-SRS-EVID-003:** PLOC may be a bounded prior for locus refinement, but refinement shall remain within documented local bounds.
- **TR-SRS-EVID-004:** Observed measurements and derived scores shall remain distinguishable.

## 4. Evidence profiles

- **TR-SRS-PROF-001:** A profile shall preserve relative A/C/G/T evidence beyond the primary call.
- **TR-SRS-PROF-002:** Uncalibrated profile values shall be called evidence weights, not allele fractions or probabilities.
- **TR-SRS-PROF-003:** Flat/unresolved evidence shall remain explicitly unresolved.
- **TR-SRS-PROF-004:** Profile construction shall be deterministic, finite, bounded, and method-versioned.

## 5. Alignment

- **TR-SRS-ALI-001:** Profile-aware alignment shall reuse one authoritative affine-gap DP/traceback implementation unless evidence justifies replacement.
- **TR-SRS-ALI-002:** Scoring shall define reverse-complement, coordinate, tie-break, circular-reference, gap, and unresolved-evidence semantics.
- **TR-SRS-ALI-003:** Clean canonical traces shall be benchmarked against the current primary-sequence alignment baseline.

## 6. Variant evidence

- **TR-SRS-VAR-001:** Mixed supporting evidence shall be distinguishable from a clean canonical supporting call.
- **TR-SRS-VAR-002:** Simple-variant reporting shall not silently reinterpret unresolved mixed evidence as a clean substitution.
- **TR-SRS-VAR-003:** Deleted reference bases shall not be assigned fabricated trace-base evidence.

## 7. Sample-level analysis

- **TR-SRS-SAMPLE-001:** Sample-level analysis shall be layered above completed single-trace observations.
- **TR-SRS-SAMPLE-002:** Every consensus observation shall retain provenance to contributing traces/calls.
- **TR-SRS-SAMPLE-003:** Read admission, consensus reconciliation, and variant filtering shall remain separate decisions.
- **TR-SRS-SAMPLE-004:** Contradictory high-quality evidence shall remain explicit rather than being hidden by majority voting.
- **TR-SRS-SAMPLE-005:** Initial multi-read consensus shall be reference-guided in reference coordinates.

## 8. Mixed signal and indels

- **TR-SRS-MIX-001:** Persistent mixed-signal detection may report a breakpoint/phase-shift hypothesis without assigning genotype.
- **TR-SRS-MIX-002:** Tracy's diploid/two-allele interpretation shall not be mapped directly onto mtDNA.
- **TR-SRS-MIX-003:** Heteroplasmy fraction, genotype, or LoD claims require controlled mixtures or independent truth and assay-specific validation.
- **TR-SRS-MIX-004:** Homopolymer/poly-C contexts shall expose representation or alignment instability when multiple placements are plausible.

## 9. Output contracts

- **TR-SRS-OUT-001:** Research evidence shall not expand compact production result schemas by default.
- **TR-SRS-OUT-002:** Bulk trace/profile/review evidence, if promoted, shall use a separate opt-in independently versioned contract.
- **TR-SRS-OUT-003:** VCF/BCF or other interchange formats shall be projections from authoritative typed results.

## 10. Determinism and validation

- **TR-SRS-ENG-001:** Every promoted algorithm shall define deterministic ordering, tie-breaking, floating-point/quantization rules, and strand behavior.
- **TR-SRS-ENG-002:** Memory and runtime shall be explicitly bounded before production promotion.
- **TR-SRS-VAL-001:** Validation shall include synthetic units, synthetic chromatogram shapes, and a provenanced real AB1 corpus.
- **TR-SRS-VAL-002:** Mixed-template/heteroplasmy/genotype/calibration claims require independent truth beyond agreement with Tracy.
- **TR-SRS-VAL-003:** Each promoted phase shall compare against the current Signal baseline and document regressions as well as improvements.
