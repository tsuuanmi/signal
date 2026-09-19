# Event-Placement Diagnostics

## Purpose

Investigate large disagreements between primary basecalls and continuous nucleotide-profile evidence before any profile-geometry threshold is fitted.

The initial local validation study confirmed that the previous global-within-window total-signal maximum could associate a locus with a neighboring event. Extreme profile disagreements were concentrated in observations where the evidence event was displaced by roughly one local peak spacing while the primary call remained coherent at its own event. Exact sample-level measurements remain local validation artifacts.

## Hypothesis under test

Basecalling and `LocusEvidence` use the same PLOC-defined window but different event-selection rules.

Basecalling:

```text
select one local peak per channel
-> choose uniquely strongest channel peak as primary event
```

Signal evidence:

```text
scan every sample in the PLOC window
-> choose the sample maximizing total corrected A+C+G+T amplitude
```

Therefore an evidence profile can, in principle, be evaluated at a different sample position from the primary basecall event. Validation must measure that displacement directly before changing either rule.

## Diagnostic questions

For loci with unexpectedly low called/reference profile mass or high read/read geometry, inspect each observation:

1. Does the signal-evidence event equal the primary-peak position?
2. If not, how many chromatogram samples separate them?
3. Is the evidence event displaced toward another channel-local peak?
4. Is the displacement shared across reads or specific to one direction?
5. Does the reference-oriented profile agree with `aligned_base` at the primary peak but not at the refined event?
6. Are large displacements concentrated near read ends, homopolymers, candidate-noisy regions, or alignment boundaries?

## Required measurements

`signal.validation_locus/v2` preserves the existing locus geometry and adds nested read diagnostics containing call identity, PLOC/window coordinates, primary-peak placement, evidence-event placement, reference-oriented per-channel peak/signal/profile evidence, quality, orientation, and noisy-region membership.

Source chromatogram coordinates are never reversed. A/C/G/T arrays are always projected to the selected reference orientation.

## Interpretation discipline

Do not classify a locus as artifact merely because event and primary positions differ. A small displacement can be biologically reasonable when channels are phase-shifted or secondary signal is offset.

Do not classify a mixed profile as heteroplasmy from these diagnostics. The purpose is only to explain where the profile was measured and whether independent reads reproduce the same event geometry.

Do not fit profile-geometry thresholds until unexplained extreme event-placement cases have been characterized.

## Resolution and revalidation

ADR-0046 replaces the global maximum rule with the positive total-signal local maximum nearest PLOC, retaining basecall-independent composition while preventing stronger neighboring events from stealing the locus profile. Synthetic regression fixtures encode the neighboring-event failure mode.

The next validation step is to rerun the same local corpus through `signal.validation_locus/v2` and verify that:

- previously extreme event/primary displacements collapse to the PLOC-local event;
- ordinary near-zero/one-sample offsets remain stable;
- reference-called profile mass and F/R geometry improve without erasing genuine mixed-channel profiles;
- alignment/variant changes are reviewed rather than assumed beneficial.

The first post-ADR-0046 rerun showed the extreme event-placement tail collapse while ordinary near-zero offsets remained stable. A residual indel-adjacent case exposed a separate alignment question: repeat-equivalent gap placements can move primary calls between reference loci even when the underlying read sequence is unchanged. That issue is not evidence that basecalling should be forced toward PLOC; it is now governed by ADR-0047, which requires canonical 3'/right-most mtDNA gap placement among equivalent optimal alignments.

Threshold fitting remains paused until event association and canonical alignment are both empirically revalidated.
