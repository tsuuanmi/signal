# Read-local poly-C phase measurement

`signal.polyc_phase/v1` is the current internal production measurement for mtDNA
post-poly-C phase evidence.

## Applicability

The method runs only for the exact circular rCRS sequence identity adopted by ADR-0056
and verifies the canonical HV2 303–315 and HV1 16184–16193 tract sequences.

Other references are `NotApplicable`; Signal does not fall back to a generic homopolymer
detector.

## Placement dependency

Measurement runs after selected alignment and consumes:

- selected orientation and reference-coordinate path;
- original call indexes retained by alignment;
- existing basecall-independent `EvidenceProfile` records;
- immutable rCRS sequence context.

It cannot alter alignment, calls, quality, or variants.

## Availability

Each supported tract is retained as either:

- measured;
- insufficient because the tract is not covered;
- insufficient because tract coverage is partial;
- insufficient because no tract position is call-backed;
- insufficient because fewer than 25 profile-bearing post-tract observations can form one
  complete window.

Insufficient evidence is not interpreted as stable phase.

## Window and candidate method

Windows contain 25 consecutive profile-bearing post-tract observations in read-order
reference distance, with stride 5. Missing profiles are skipped without synthesis.

Every window retains the complete candidate curve for offsets:

```text
-5 -4 -3 -2 -1 +1 +2 +3 +4 +5
```

A position is informative for a candidate only when the represented shifted reference base
exists, is canonical A/C/G/T, and differs from the zero-phase reference base.

For each candidate Signal retains informative-position count and mean:

- zero-reference profile mass;
- shifted-reference profile mass;
- residual profile mass.

No winning candidate, phase class, recovery state, confidence value, or sample weight is
computed.

## Public behavior

Phase evidence is retained only in internal `ReadObservation` and concise operational
availability logging. Current analysis/sample JSON schemas and configuration remain
unchanged.

See ADR-0055, ADR-0056, and
[the promotion protocol](../validation/polyc-phase-promotion.md).
