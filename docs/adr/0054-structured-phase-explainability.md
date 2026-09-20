# ADR-0054: Separate structured phase explainability from unstructured signal degradation

- **Status:** Accepted
- **Date:** 2026-09-20
- **Implementation:** Research-only candidate phase-hypothesis measurement; no production calling change.

## Context

ADR-0052 establishes that evidence after an unstable mtDNA poly-C tract is
directionally lower-confidence. The first full-corpus poly-C study shows that this
post-tract evidence is not homogeneous.

Some affected reads retain a coherent sequence-offset pattern: signal at many consecutive
positions is partly explained by the reference sequence shifted by one or more positions.
Other regions are simply impure/noisy and may not be explained well by any stable
reference offset.

These two conditions have different scientific consequences:

- **structured dephasing** may retain usable sequence information, although it should not
  be treated as equivalent to clean phase-coherent evidence;
- **unstructured degradation** has poor explanatory structure and may ultimately justify
  very low contribution or no call.

A single post-poly-C badness score would collapse these distinct states.

Tracy's indel decomposition provides a useful algorithmic principle. After detecting a
persistent trace transition, Tracy evaluates multiple downstream insertion/deletion
offsets and asks which offset makes the downstream primary/secondary evidence most
consistent with the reference. The useful lesson is the candidate explanatory curve and
downstream persistence, not Tracy's diploid allele interpretation or reference-driven
rewriting of observed calls.

## Decision

Signal will research post-poly-C phase behavior along two independent dimensions:

1. **phase explainability** — how much observed profile mass is explained by a coherent
   reference offset across a downstream window;
2. **unexplained residual** — how much profile mass remains outside both the unshifted
   and candidate-shifted reference bases.

The first implementation MUST remain descriptive and MUST NOT combine these dimensions
into a production confidence score.

### Candidate reference offsets

For each post-tract window, evaluate zero phase plus a bounded set of non-zero integer
reference offsets in **sequencing order**.

An offset is not called an insertion or deletion. It means only:

> At this observation, compare the measured A/C/G/T profile with the reference base that
> occurs the candidate number of reference positions away in the selected read direction.

This avoids prematurely assigning biological indel semantics to polymerase slippage,
length heterogeneity, or other mixed-template effects.

### Informative positions

A position contributes to a non-zero candidate only when the unshifted reference base and
the offset reference base differ.

Positions where both hypotheses predict the same nucleotide contain no information for
distinguishing those phases and MUST NOT dilute candidate evidence.

### Candidate evidence

For every candidate offset and window, retain at least:

- number of informative positions;
- mean profile mass on the unshifted reference base;
- mean profile mass on the candidate-shifted reference base;
- mean residual profile mass assigned to the other bases.

The residual is descriptive. Low residual with substantial shifted-reference mass is
consistent with structured phase mixture. High residual indicates that a simple phase
offset does not explain the observed signal well.

Signal MUST preserve the complete candidate curve rather than emitting only a winning
offset.

### Window persistence

Candidate hypotheses MUST be evaluated over multiple consecutive downstream observations,
not one focal variant.

This protects against interpreting a true local SNV or isolated artifact as a persistent
phase shift. Window start/end and tract distance remain explicit provenance.

Initial research window size, stride, and maximum tested offset are research parameters
recorded in the artifact method metadata. They are not production thresholds.

### Observation immutability

Reference hypotheses MUST NOT rewrite:

- primary calls;
- ambiguity calls;
- EvidenceProfile values;
- alignment;
- variant observations.

Reference consistency is evaluated against immutable measured evidence only.

## Interpretation model

The research is intentionally two-dimensional:

```text
                         high residual
                              ^
                              |
           degraded           |       shifted + degraded
                              |
    --------------------------+------------------------> phase explainability
                              |
        clean/unaffected      |       structured dephasing
                              |
                         low residual
```

The exact boundaries between these states are not defined by this ADR.

## Relationship to Tracy

Signal adopts from Tracy:

- persistent downstream behavior rather than single-locus ambiguity;
- explicit evaluation of multiple candidate offsets;
- preservation of the full candidate error/evidence curve;
- comparison of a candidate against zero shift and neighboring alternatives.

Signal does **not** adopt:

- diploid two-allele semantics;
- automatic heterozygous-indel interpretation;
- reference-threading that mutates primary/secondary observations;
- Tracy's fixed breakpoint, MAD, or candidate-selection thresholds as Signal thresholds.

Those numeric rules were designed for Tracy's decomposition task and require independent
validation for mtDNA poly-C behavior.

## Consequences

- Post-poly-C evidence can eventually be treated differently when it is coherently
  dephased versus simply degraded.
- A true isolated point variant should not receive strong phase support unless an offset
  also explains surrounding observations.
- Phase recovery can later be studied as the disappearance of coherent shifted evidence
  and residual degradation across successive windows, without a fixed genomic recovery
  distance.
- Candidate offset magnitude may become evidence about length mixture, but it is not a
  biological indel call by itself.
- Any future production contribution weight must depend on validated evidence and remain
  a separate promotion decision.

## Non-goals

This ADR does not define a breakpoint caller, phase-state classifier, genotype, length
heteroplasmy estimate, indel call, demixed sequence, recovery threshold, confidence
multiplier, no-call rule, or production output field.
