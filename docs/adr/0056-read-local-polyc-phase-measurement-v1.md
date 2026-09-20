# ADR-0056: Implement continuous read-local poly-C phase measurement v1

- **Status:** Accepted
- **Date:** 2026-09-20
- **Implementation:** Implemented as internal read-local evidence only; no phase state, weighting, no-call, variant mutation, config key, or public-schema change.

## Context

ADR-0055 defines the production boundary for future read-local mtDNA poly-C phase evidence.
The completed validation research established one stable descriptive candidate method and
showed that the main C-interrupt / shifted-reference findings persist across the tested
window-size, stride, and maximum-offset grid.

A production measurement can therefore be implemented without promoting a categorical
detector or reliability policy, provided it preserves the same candidate-wise evidence
semantics and leaves all existing calling/reconciliation behavior unchanged.

## Decision

Signal implements internal method `signal.polyc_phase/v1`.

The method runs after selected alignment and before cross-read reconciliation. It is
continuous evidence only.

### Applicability

The method is applicable only when all of the following hold:

- the supplied reference topology is circular;
- normalized reference length is 16,569;
- normalized reference sequence SHA-256 is
  `f156ff3f65bbcc80c7ebb9936dceb96b1477b4f8f535c4e1dbe7baea225cbc66`;
- the canonical rCRS HV2 and HV1 tract sequences are present exactly:
  - HV2 303–315: `CCCCCCCTCCCCC`;
  - HV1 16184–16193: `CCCCCTCCCC`.

Otherwise the read-level result is `NotApplicable`. No generic homopolymer fallback is
permitted.

### Tract coverage and sequencing order

For each supported tract, reference positions are taken only from the selected alignment.

- zero represented tract positions -> insufficient `NoTractCoverage`;
- partial represented tract -> insufficient `IncompleteTractCoverage`;
- complete represented tract with no call-backed tract position -> insufficient
  `NoCallBackedTractSpan`.

The tract call span is derived from original trace call indexes. A call-backed aligned
observation is post-tract only when its original call index is greater than the maximum
call-backed tract index.

Reference distance after the tract follows selected sequencing orientation on circular
rCRS:

- forward exits at the tract's high coordinate and increases through the origin;
- reverse exits at the tract's low coordinate and decreases through the origin.

This preserves actual read history rather than linear reference-coordinate ordering.

### Reference-oriented profiles

A call-backed post-tract observation uses the existing basecall-independent
`EvidenceProfile` for that original call index.

Forward profiles are retained as-is. Reverse profiles are reverse-strand complemented into
reference A/C/G/T channel order.

Missing profiles remain missing and are never synthesized.

### Window method constants

The v1 measurement method uses the research-promoted constants:

```text
profile-bearing observations per window = 25
window stride in profile-bearing observations = 5
candidate reference offsets in read order = -5..-1, +1..+5
```

These are method constants, not user configuration and not detector thresholds.

Windows are constructed from consecutive **profile-bearing** post-tract observations
sorted by positive read-order reference distance. Missing-profile observations are skipped
rather than filled or converted into interval membership.

Fewer than 25 eligible profile observations produces insufficient
`NoCompleteProfileWindow`.

### Candidate evidence

For every window and every declared non-zero candidate offset, a locus contributes only
when:

- the candidate shifted reference distance is represented by a call-backed post-tract
  observation;
- both zero-phase and shifted reference bases are canonical A/C/G/T;
- the shifted reference base differs from the zero-phase reference base.

For informative positions retain:

- informative-position count;
- mean profile mass on the zero-phase reference base;
- mean profile mass on the candidate-shifted reference base;
- mean residual mass on the remaining bases.

A candidate with zero informative positions retains count zero and absent mean masses.

The full ten-candidate curve is retained in deterministic offset order. No winning offset
is selected.

Each window also retains exact start/end read-order reference distance, start/end original
call index, profile-observation count, mean profile impurity, and mean zero-reference mass.

### Interrupt observation

For each completely represented tract, the aligned query base at T310/T16189 is retained
only when it is a call-backed canonical A/C/G/T observation. It is descriptive read-local
evidence and is not interpreted as genotype or tract truth.

### Production consequences

`ReadObservation` retains the internal `ReadPhaseEvidence`, and operational logging
records only applicability/coverage counts and method constants.

The measurement MUST NOT change:

- selected alignment;
- primary/ambiguity calls;
- variant extraction, normalization, or eligibility;
- sample structural contribution eligibility;
- unit-mass nucleotide support;
- public analysis/sample schemas;
- configuration schema.

## Validation

The Rust implementation is required to test:

- unsupported-reference non-applicability;
- exact complete/incomplete tract coverage semantics;
- explicit insufficient-window behavior;
- profile-gap window construction without interval fallback;
- forward/reverse reference-oriented profile projection;
- circular HV1/HV2 distance geometry;
- candidate informative-position filtering;
- shifted/zero/residual mass decomposition;
- complete deterministic candidate curves.

The existing Python research artifacts remain descriptive validation evidence, not a
runtime dependency.

Any later categorical phase interpretation, recovery rule, attenuation, contribution
weight, or no-call still requires the promotion protocol in
`docs/validation/polyc-phase-promotion.md` and a separate accepted decision.

## Consequences

- Signal now has one authoritative production measurement path rather than research-only
  evidence semantics.
- Research and Rust share the same scientific window/candidate definitions without a
  runtime Python dependency.
- The measurement is observable internally but has no calling consequence.
- Future reliability policy can consume one explicit read-local evidence type rather than
  re-derive phase geometry inside sample reconciliation.

## Non-goals

This ADR does not define a `PhaseState`, candidate winner, breakpoint, recovery cutoff,
confidence value, sample weighting, artifact verdict, genotype, length heteroplasmy,
public output field, or configuration parameter.
