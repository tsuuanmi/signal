# Tracy-Informed Research Software Requirements Specification

## 1. Purpose

This SRS defines requirements for Tracy-inspired research inside Signal. It mirrors the role of the root Signal SRS but is not a production contract. A requirement here becomes normative only after promotion through the root ADR/SRS/schema process and implementation.

## 2. Scope boundary

- **TR-SRS-SCOPE-001:** Improve biological correctness, evidence preservation, reviewability, or a demonstrated engineering constraint; feature parity with Tracy is not a goal.
- **TR-SRS-SCOPE-002:** The current single-trace Signal pipeline remains the production baseline until a root-level decision changes it.
- **TR-SRS-SCOPE-003:** Tracy behavior is comparison evidence, not ground truth.
- **TR-SRS-SCOPE-004:** Research documents shall distinguish proposed behavior from implemented behavior.

## 3. Input and event-anchor requirements

- **TR-SRS-IN-001:** The current PLOC dependency shall be explicit as a scientific input assumption, not only a parser requirement.
- **TR-SRS-IN-002:** Research shall distinguish usable/complete PLOC evidence from suspicious or incomplete PLOC evidence where the available trace metadata permits that distinction.
- **TR-SRS-IN-003:** A future PLOC-independent event detector shall be a separately versioned calling method rather than an undocumented fallback that changes method semantics.
- **TR-SRS-IN-004:** PLOC/basecall length inconsistencies, implausible spacing, or premature event termination shall be reportable as evidence-quality conditions before downstream interpretation.

## 4. Locus evidence

- **TR-SRS-EVID-001:** Richer locus evidence shall retain original call index, PLOC/sample coordinates, canonical A/C/G/T channel order, and method identity.
- **TR-SRS-EVID-002:** Secondary evidence shall be spatially compatible with the same nucleotide event; peak strength alone is insufficient.
- **TR-SRS-EVID-003:** PLOC may be a bounded prior for locus refinement, but refinement shall remain within documented local bounds.
- **TR-SRS-EVID-004:** Observed measurements and derived scores shall remain distinguishable.
- **TR-SRS-EVID-005:** Artifact observations such as saturation/clipping, high-amplitude local outliers, baseline shifts, and neighboring-event interference shall remain distinct from biological mixed-signal interpretation.
- **TR-SRS-EVID-006:** Artifact handling should use local robust evidence where possible and shall not allow one high-amplitude event to redefine the biological strength of unrelated loci without explicit justification.

## 5. Evidence profiles

- **TR-SRS-PROF-001:** A profile shall preserve relative A/C/G/T evidence beyond the primary call.
- **TR-SRS-PROF-002:** Uncalibrated profile values shall be called evidence weights, not allele fractions or probabilities.
- **TR-SRS-PROF-003:** Flat/unresolved evidence shall remain explicitly unresolved.
- **TR-SRS-PROF-004:** Profile construction shall be deterministic, finite, bounded, and method-versioned.
- **TR-SRS-PROF-005:** Profile construction shall not discard a channel solely because that channel failed the current ambiguity/basecall threshold; thresholded primary/ambiguity calls are projections of evidence, not the definition of the evidence profile.
- **TR-SRS-PROF-006:** Profile normalization shall document its denominator, behavior under zero/near-zero total evidence, and treatment of unresolved mass.

## 6. Alignment

- **TR-SRS-ALI-001:** Profile-aware alignment shall reuse one authoritative affine-gap DP/traceback implementation unless evidence justifies replacement.
- **TR-SRS-ALI-002:** Scoring shall define reverse-complement, coordinate, tie-break, circular-reference, gap, and unresolved-evidence semantics.
- **TR-SRS-ALI-003:** Clean canonical traces shall be benchmarked against the current primary-sequence alignment baseline.
- **TR-SRS-ALI-004:** Profile substitution scores shall use an explicitly deterministic numeric/quantization policy; implicit floating-point-to-integer truncation shall not define scientific behavior.
- **TR-SRS-ALI-005:** Equal orientation/alignment scores shall have an explicit semantic outcome; a hidden implementation-order bias shall not be mistaken for biological evidence.
- **TR-SRS-ALI-006:** Circular-origin behavior already supported by Signal shall remain a regression-protected invariant when profile scoring is introduced.

## 7. Variant evidence

- **TR-SRS-VAR-001:** Mixed supporting evidence shall be distinguishable from a clean canonical supporting call.
- **TR-SRS-VAR-002:** Simple-variant reporting shall not silently reinterpret unresolved mixed evidence as a clean substitution.
- **TR-SRS-VAR-003:** Deleted reference bases shall not be assigned fabricated trace-base evidence.
- **TR-SRS-VAR-004:** Reference-aware interpretation shall not mutate the underlying observed basecall/signal evidence.
- **TR-SRS-VAR-005:** Genotype, zygosity, heteroplasmy fraction, or calibrated genotype-quality semantics shall not be inferred from Tracy-compatible heuristics alone.
- **TR-SRS-VAR-006:** Variant projections shall preserve authoritative mappings among reference position, original call index, and trace/PLOC sample position.

## 8. Sample-level analysis

- **TR-SRS-SAMPLE-001:** Sample-level analysis shall be layered above completed single-trace observations.
- **TR-SRS-SAMPLE-002:** Every consensus observation shall retain provenance to contributing traces/calls.
- **TR-SRS-SAMPLE-003:** Read admission, consensus reconciliation, and variant filtering shall remain separate decisions.
- **TR-SRS-SAMPLE-004:** Contradictory high-quality evidence shall remain explicit rather than being hidden by majority voting.
- **TR-SRS-SAMPLE-005:** Initial multi-read consensus shall be reference-guided in reference coordinates.
- **TR-SRS-SAMPLE-006:** Pairwise/multi-read reconciliation shall define explicit minimum overlap and agreement/read-admission criteria before consensus.
- **TR-SRS-SAMPLE-007:** Consensus shall preserve per-observation evidence through the locus decision rather than reducing admitted reads to unweighted character voting.
- **TR-SRS-SAMPLE-008:** Gap/insertion/deletion support shall be modeled explicitly; a gap shall not receive a fabricated nucleotide-like quality solely to fit one scoring interface.
- **TR-SRS-SAMPLE-009:** Fractional coverage requirements shall define deterministic rounding and local denominators; integer truncation shall not silently weaken admission rules.
- **TR-SRS-SAMPLE-010:** Consensus quality shall not be labeled Phred/calibrated error probability until validated as such.

## 9. Mixed signal and indels

- **TR-SRS-MIX-001:** Persistent mixed-signal detection may report a breakpoint/phase-shift hypothesis without assigning genotype.
- **TR-SRS-MIX-002:** Tracy's diploid/two-allele interpretation shall not be mapped directly onto mtDNA.
- **TR-SRS-MIX-003:** Heteroplasmy fraction, genotype, or LoD claims require controlled mixtures or independent truth and assay-specific validation.
- **TR-SRS-MIX-004:** Homopolymer/poly-C contexts shall expose representation or alignment instability when multiple placements are plausible.
- **TR-SRS-MIX-005:** Change-point and candidate-shift algorithms shall operate on immutable evidence and return new hypothesis objects rather than rewriting observed calls.
- **TR-SRS-MIX-006:** Reference consistency may rank hypotheses but shall not erase competing chromatogram evidence.

## 10. Output contracts

- **TR-SRS-OUT-001:** Research evidence shall not expand compact production result schemas by default.
- **TR-SRS-OUT-002:** Bulk trace/profile/review evidence, if promoted, shall use a separate opt-in independently versioned contract.
- **TR-SRS-OUT-003:** VCF/BCF or other interchange formats shall be projections from authoritative typed results.
- **TR-SRS-OUT-004:** A future review/evidence artifact should preserve enough coordinate provenance to link a reported event back to its contributing trace call and raw-signal location without recomputing scientific mappings.

## 11. Determinism and validation

- **TR-SRS-ENG-001:** Every promoted algorithm shall define deterministic ordering, tie-breaking, floating-point/quantization rules, and strand behavior.
- **TR-SRS-ENG-002:** Memory and runtime shall be explicitly bounded before production promotion.
- **TR-SRS-VAL-001:** Validation shall include synthetic units, synthetic chromatogram shapes, and a provenanced real AB1 corpus.
- **TR-SRS-VAL-002:** Mixed-template/heteroplasmy/genotype/calibration claims require independent truth beyond agreement with Tracy.
- **TR-SRS-VAL-003:** Each promoted phase shall compare against the current Signal baseline and document regressions as well as improvements.
- **TR-SRS-VAL-004:** The validation corpus shall include adversarial artifact cases, suspicious/incomplete PLOC cases, unequal-quality read conflicts, base-versus-gap conflicts, origin-crossing circular alignments, and clean controls.
- **TR-SRS-VAL-005:** A Tracy disagreement shall be classified as Signal regression, intentional correction, unresolved evidence difference, or Tracy limitation before changing production behavior.
