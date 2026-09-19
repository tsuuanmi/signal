# ADR-0045: Export validation event-placement diagnostics

- **Status:** Accepted
- **Date:** 2026-09-19

## Context

Threshold research can encounter loci where primary basecalls agree with the reference
while continuous nucleotide profiles disagree strongly across reads or place little mass
on the called/reference nucleotide.

Signal currently derives basecalls and `EvidenceProfile` from the same PLOC window but
with different event-selection rules:

- basecalling selects channel-local peaks and a uniquely strongest primary channel;
- signal evidence selects the sample position with maximum total non-negative
  baseline-corrected A/C/G/T amplitude.

Before changing either scientific rule, validation must expose enough provenance to
determine whether large profile disagreement reflects real mixed signal, neighboring-event
selection, read-end behavior, alignment context, or another mechanism.

## Decision

`signal.validation_locus/v2` replaces validation-locus v1 and adds one nested diagnostic
record per retained read observation.

For every call-backed observation the diagnostic record includes:

- read SHA-256 and selected alignment orientation;
- locus state, reference-oriented aligned base, quality, and original call index;
- source-trace primary and ambiguity calls;
- PLOC and call-window coordinates;
- primary-peak position and offset from PLOC;
- signal-evidence event position and offset from PLOC;
- event offset from the primary-peak position;
- selected channel-peak positions, heights, and peak-source kinds;
- raw primary-peak channel heights projected to reference-oriented A/C/G/T;
- corrected amplitudes, SNRs, and normalized profile projected to reference-oriented
  A/C/G/T;
- candidate-noisy-region membership.

Deletion observations retain null call/event diagnostics because they do not correspond
to a source nucleotide call.

All A/C/G/T arrays in the validation diagnostic contract are reference-oriented. Sample
coordinates remain coordinates on the source chromatogram and are never reversed.

The exporter performs no event re-selection, thresholding, conflict classification, or
scientific correction.

## Consequences

- Validation can directly compare basecall primary-event placement with profile-event
  placement for the same source call.
- Reverse-read channel evidence is not misread as strand-discordant because diagnostic
  arrays use the same reference orientation as sample profile evidence.
- An eventual scientific change can be justified by empirical event-placement evidence
  rather than by threshold tuning around unexplained outliers.

## Non-goals

No basecalling change, event-selection change, threshold, artifact classifier, consensus
rule, heteroplasmy inference, or public production-schema change is introduced.
