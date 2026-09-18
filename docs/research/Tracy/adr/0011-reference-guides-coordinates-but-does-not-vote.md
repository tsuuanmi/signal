# ADR-0011: Reference Guides Coordinates but Does Not Vote as Sample Evidence

- **Status:** Accepted for research
- **Date:** 2026-09-18

## Context

Tracy reference-guided assembly uses the reference to guide placement. Historical
issue discussion around `--incref` also shows that including the reference in
consensus computation changes tie outcomes.

A reference sequence and an observed chromatogram have different epistemic roles:

- the reference supplies coordinate/context expectations;
- reads supply evidence about the sample.

Treating the reference as an ordinary observation risks converting prior
expectation into apparent sample support.

## Decision

By default, Signal sample consensus shall use references for coordinate
placement, normalization, topology, and interpretation context, but shall not
count reference bases as independent sample observations or consensus votes.

Any future reference-prior model that influences a consensus decision must be
explicitly named, versioned, and distinguish prior contribution from observed
trace support.

## Consequences

A one-read locus remains one-read evidence even when the reference agrees with
it. Reference agreement can be reported or used for hypothesis ranking, but it
cannot silently increase observed support.
