# Implementation Direction

This plan is constrained by [`requirements.md`](requirements.md), [`architecture.md`](architecture.md), and the research ADRs under [`adr/`](adr/README.md). Detailed scientific rationale lives in the focused feature notes; this file focuses on integration order and PR boundaries.

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

The source audit adds one important ordering constraint: richer profile
interpretation must not outrun validation of the event/evidence foundation.

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

## Phase 1A: harden event/evidence diagnostics

### Goal

Before changing alignment semantics, make the current PLOC dependency and the
known artifact boundary explicit and testable.

Research/validation work should cover:

- suspicious or prematurely terminated PLOC series;
- implausible local call spacing;
- saturation/clipping;
- broad high-amplitude dye-blob-like events;
- large local outliers over otherwise usable sequence;
- baseline shift and neighboring-event interference.

This phase should prefer observation/diagnostic additions over automatic
waveform correction. A future PLOC-independent event detector would be a new
method version, not a silent fallback.

### Why before profiles

Tracy's profile construction demonstrates that richer downstream
representations cannot recover evidence that was already mischaracterized
upstream. Public Tracy issues also show complete basecalling failure on some
high-amplitude artifacts and hard dependence on instrument peak positions.

Signal's existing rolling local SNR is useful, but remains observation-only; it
must not be cited as evidence that the caller is already artifact-resilient.

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

Do not port Tracy's `createProfile` formula verbatim. Tracy first decides
which channels belong to the primary/secondary call and only then constructs a
profile from those admitted channels, softening missing called-signal mass
toward a uniform vector. Signal should avoid making the ambiguity threshold the
definition of downstream evidence.

Evaluate profiles built directly from Signal's own evidence:

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

Whichever boundary is chosen, observed/basecall evidence remains immutable under
later reference-aware interpretation.

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

This is only a conceptual starting point. Tracy computes a floating expected
match/mismatch score and then casts it to an integer before DP recursion; Signal
should instead make numeric quantization part of the method contract.

Before implementation, define behavior for:

- unresolved/flat profiles;
- `N` in the reference;
- floating-point determinism and tie breaking;
- reverse-complement transformation;
- gap scoring;
- circular references;
- minimum identity/callable metrics;
- fixed numeric/quantization rules;
- exact orientation and traceback tie semantics.

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
- reference-coordinate overlap and admission criteria;
- per-locus evidence reconciliation;
- nucleotide versus gap/indel event support;
- disagreement classification;
- consensus confidence;
- provenance of every contributing trace.

Unlike Tracy `assemble`, this layer should not reduce admitted reads to
quality-blind majority voting before the final decision.

## Phase 5: reference-guided multi-trace consensus

Generalize the same sample-level model from two opposite-strand reads to
multiple overlapping traces.

The first version should require a reference and operate in reference
coordinates. De novo assembly remains deferred.

Important invariants:

- every consensus locus links back to contributing trace calls;
- poor or ambiguous reads do not gain equal weight automatically;
- local coverage denominator and any fractional threshold are explicit;
- gap/indel support is modeled explicitly rather than assigned fake base quality;
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
Reference consistency may rank hypotheses but must not rewrite the underlying
primary/secondary or signal evidence.

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

2. **PLOC/artifact evidence diagnostics**
   - explicit PLOC completeness/suspicion semantics;
   - synthetic dye-blob/saturation/outlier cases;
   - observation-first artifact flags;
   - no automatic waveform repair.

3. **Nucleotide evidence profile**
   - typed internal representation;
   - direct channel-evidence construction independent of ambiguity threshold;
   - deterministic normalization;
   - no behavior change yet if possible.

4. **Evidence-aware alignment**
   - generalized scorer;
   - validation against current clean-call behavior;
   - targeted ambiguous/noisy synthetic cases.

5. **Two-trace reconciliation model**
   - forward/reverse evidence in reference coordinates;
   - no full sample assembly yet.

6. **Reference-guided sample consensus**
   - multiple overlapping traces;
   - explicit provenance and disagreement.

7. **Mixed-signal breakpoint research**
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
- explicit behavior for incomplete/suspicious PLOC evidence;
- explicit behavior for high-amplitude artifacts and saturation;
- explicit behavior for mixed and unresolved calls;
- explicit nucleotide-versus-gap conflict behavior;
- bounded memory/runtime;
- schema stability unless intentionally versioned;
- controlled synthetic examples before claims on real biological mixtures.

For consensus or mixed-template work, real-data claims require approved
replicates or controlled mixtures with known truth. Tracy is a design reference,
not ground truth for Signal.
