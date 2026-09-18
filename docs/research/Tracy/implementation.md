# Implementation Direction

This document translates the high-ROI Tracy lessons into Signal's current
architecture. It is a design sequence, not an approved implementation contract.

Current core flow:

```text
trace
  -> basecalling
  -> signal_processing
  -> quality_control
  -> retained primary sequence
  -> alignment
  -> variant_calling
  -> report
```

The intended evolution is incremental. Each step should remain independently
useful and should not require the later steps to justify it.

## Phase 1: distinguish simple variants from mixed supporting signal

### Goal

Keep the current primary-sequence caller, but stop treating a mixed supporting
locus as equivalent to a clean canonical call when deciding whether a candidate
belongs in the "simple/easy variant" result.

### Existing inputs

`src/model/basecalls.rs` already retains:

- `primary`;
- `ambiguity`;
- qualifying channels;
- selected A/C/G/T peaks;
- original call index and PLOC.

`src/variant_calling/filter.rs` already centralizes supporting-evidence
eligibility.

### Proposed behavior

For SNVs and inserted supporting calls:

```text
canonical primary
+ no unresolved/mixed ambiguity for the supporting call
+ existing peak floor
+ existing relative-quality gate
= simple-variant-eligible
```

A mixed call should receive a distinct exclusion reason rather than being
silently folded into the existing peak/quality failures.

Deletions remain different because there is no trace call for the deleted
reference bases.

### Expected files when implemented

```text
src/model/variant.rs
src/variant_calling/filter.rs
docs/src/model/variant.md
docs/src/variant_calling/filter.md
docs/pipeline.md
docs/json-output.md or next schema docs if warnings change
focused tests
```

If the serialized warning contract changes, it requires an explicit schema
version decision rather than an incidental field addition.

## Phase 2: introduce an internal nucleotide evidence profile

### Goal

Create a typed per-locus representation that preserves the relative evidence
for A/C/G/T and can be consumed by alignment or later consensus code.

### Boundary

The profile should be scientific internal state, not a report-layer object.

A possible conceptual type is:

```rust
struct NucleotideEvidence {
    a: f32,
    c: f32,
    g: f32,
    t: f32,
}
```

The final representation may use an array indexed by the existing nucleotide
enum instead. The important invariants are:

- canonical fixed A/C/G/T ordering;
- finite values;
- deterministic construction;
- documented normalization;
- no hidden dependence on vendor PBAS/PCON;
- preserved mapping to the original call index.

### Evidence source

Do not port Tracy's `createProfile` formula verbatim. Evaluate profiles built
from Signal's own evidence:

1. selected peak heights;
2. co-located channel values at the primary peak;
3. baseline-corrected local channel values;
4. local per-channel SNR;
5. combinations of the above with bounded normalization.

The first profile should be simple enough to explain and test. Empirical
validation should decide whether a more elaborate formulation is justified.

### Likely ownership

Two reasonable boundaries should be evaluated before implementation:

- a `model` evidence type constructed by a focused algorithm module; or
- an alignment-private profile when the evidence has no meaning outside
  alignment.

Prefer the first only if forward/reverse consensus or future mixed-signal
analysis will reuse exactly the same semantics.

## Phase 3: evidence-aware Gotoh alignment

### Goal

Allow a query locus to match the reference according to its nucleotide evidence
rather than only one collapsed character.

Current alignment can remain the deterministic baseline.

### Substitution concept

For reference base `G`, a simple expected-score form is:

```text
score(profile, G)
  = P(G) * match_score
  + (P(A) + P(C) + P(T)) * mismatch_score
```

This is only a conceptual starting point. Before implementation, define behavior
for:

- unresolved/flat profiles;
- `N` in the reference;
- floating-point determinism and tie breaking;
- reverse-complement transformation;
- gap scoring;
- circular references;
- minimum identity/callable metrics.

### Architecture rule

Generalize substitution scoring without duplicating the Gotoh engine. The
alignment core should have one authoritative state transition and traceback
implementation.

Potential shape:

```text
alignment/
  gotoh      -> generic DP state transitions
  scoring    -> sequence scorer + evidence-profile scorer
  orient     -> orientation comparison
  traceback  -> shared mapping reconstruction
```

The existing character-based path should not remain as an indefinite legacy
branch once an evidence-aware path is validated and selected as authoritative.

## Phase 4: forward/reverse reconciliation

### Goal

Combine independently processed traces from the same locus without breaking the
current one-trace CLI and pipeline invariants.

### Layering

```text
single-trace pipeline
        |
        +-> ReadObservation F --+
                                +-> sample reconciliation
        +-> ReadObservation R --+
```

Do not make `basecalling`, `alignment`, or `variant_calling` accept
`Vec<Trace>` merely to support consensus.

A sample-level layer can own:

- trace identity and orientation;
- reference-coordinate overlap;
- per-locus evidence reconciliation;
- disagreement classification;
- consensus confidence;
- provenance of every contributing trace.

## Phase 5: reference-guided multi-trace consensus

Generalize the same sample-level model from two opposite-strand reads to
multiple overlapping traces.

The first version should require a reference and operate in reference
coordinates. De novo assembly remains deferred.

Important invariants:

- every consensus locus links back to contributing trace calls;
- poor or ambiguous reads do not gain equal weight automatically;
- uncovered reference positions remain explicitly uncovered;
- contradictory high-quality evidence remains explicit rather than being
  silently majority-voted away;
- circular mtDNA origin handling uses the existing topology rules.

## Phase 6: persistent mixed-signal detector

### Goal

Detect a sustained change in signal character, especially the pattern that can
follow mixed-length templates, without inferring a diploid genotype.

Potential evidence:

- primary/secondary separation;
- ambiguity density;
- local SNR separation;
- call spacing instability;
- alignment mismatch/gap density;
- profile entropy or top-two evidence ratio.

Potential output is an internal diagnostic such as:

```text
breakpoint call
pre-break evidence summary
post-break evidence summary
strength/confidence
classification = unresolved_mixed_signal
```

This should first be observation-only and validated on controlled examples.

## Output strategy

The compact production result should remain compact.

New bulk evidence should prefer a separate opt-in contract, for example a future
review/evidence artifact, rather than being inserted directly into
`signal.analysis/v5`.

Derived interoperability formats such as VCF can later project from the
authoritative typed analysis result. They should not become a second scientific
implementation.

## PR sequence

Recommended independent PRs:

1. **Mixed supporting evidence gate**
   - conservative simple-variant eligibility;
   - explicit exclusion semantics;
   - synthetic unit/integration coverage.

2. **Nucleotide evidence profile**
   - typed internal representation;
   - deterministic construction;
   - no behavior change yet if possible.

3. **Evidence-aware alignment**
   - generalized scorer;
   - validation against current clean-call behavior;
   - targeted ambiguous/noisy synthetic cases.

4. **Two-trace reconciliation model**
   - forward/reverse evidence in reference coordinates;
   - no full sample assembly yet.

5. **Reference-guided sample consensus**
   - multiple overlapping traces;
   - explicit provenance and disagreement.

6. **Mixed-signal breakpoint research**
   - observation-only detector;
   - controlled validation before any biological interpretation.

Each PR should update the normative docs only when behavior actually changes.
Research notes in this directory may evolve ahead of implementation.

## Validation expectations

A Tracy-inspired feature is not complete because it reproduces Tracy on a few
examples. Signal should validate both biological behavior and system invariants.

At minimum:

- deterministic repeated results;
- forward/reverse symmetry where expected;
- coordinate and call-index preservation;
- no regression on clean single-peak traces;
- explicit behavior for mixed and unresolved calls;
- bounded memory/runtime;
- schema stability unless intentionally versioned;
- controlled synthetic examples before claims on real biological mixtures.

For consensus or mixed-template work, real-data claims require approved
replicates or controlled mixtures with known truth. Tracy is a design reference,
not ground truth for Signal.
