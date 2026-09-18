# ADR-0021: Freeze the active MVP around a scientifically correct read-level core

## Status

Proposed

## Context

Signal has accumulated useful implementations and research directions beyond the smallest viable Sanger analysis flow: rolling signal features, indel handling, circular normalization, batch orchestration, richer evidence, sample-level ideas, poly-C notes, consensus directions, and ML planning.

Those ideas may be valuable, but carrying too many of them as active roadmap commitments makes it harder to answer the most important question:

> Does Signal correctly perform the basic Sanger analysis flow, with biologically honest semantics and a clear output contract?

The project needs a stable baseline before expanding scientific scope.

## Decision

The active MVP will be defined by one narrow read-level vertical slice and reviewed through three complementary lenses:

- **signal processing:** what is measured in the chromatogram, what transformations are justified, and which evidence is preserved;
- **biology:** what biological statement the evidence actually supports, and where Signal must remain unresolved or conservative;
- **engineering:** how invariants, failure modes, determinism, schemas, and reproducibility are encoded so incorrect states are difficult to represent.

No one lens is allowed to dominate the others. A mathematically elegant signal rule is insufficient if its biological meaning is unclear; a biologically plausible rule is insufficient if it cannot be implemented and validated deterministically; a strong Rust abstraction is insufficient if it models the wrong scientific concept.

The active MVP is:

```text
AB1
 ↓
validated chromatogram decode
 ↓
primary base calling
 ↓
basic read quality / end trimming
 ↓
forward-or-reverse alignment to one short reference
 ↓
simple primary-sequence SNV detection
 ↓
clear versioned JSON result
```

The MVP is successful only when this path is scientifically understandable, deterministic, testable, and validated on approved real traces.

### Required MVP capabilities

1. **Canonical AB1 decode**
   - read the analyzed A/C/G/T channels;
   - validate FWO/channel mapping and PLOC coordinates;
   - reject malformed or inconsistent input explicitly.

2. **Primary base calling**
   - derive calls from chromatogram signal at validated loci;
   - keep primary and ambiguity concepts separate;
   - preserve enough evidence to explain a call;
   - do not silently replace source evidence with vendor PBAS.

3. **Basic quality handling**
   - remove obviously poor read ends using a documented deterministic method;
   - label any quality metric honestly if it is relative or uncalibrated;
   - avoid claiming Phred calibration without empirical evidence.

4. **Reference alignment**
   - align the retained primary sequence in both orientations;
   - select orientation deterministically;
   - preserve mapping back to original trace calls;
   - keep alignment and base calling as separate stages.

5. **Simple SNV calling**
   - report straightforward A/C/G/T primary-sequence differences;
   - exclude unresolved calls rather than guessing;
   - report coordinates and alleles on the reference strand;
   - retain direct trace-call evidence for each reported SNV.

6. **Versioned output schema**
   - make provenance, read summary, alignment summary, variants, and warnings explicit;
   - document every coordinate convention;
   - validate the schema automatically;
   - avoid unstable or redundant fields that are not needed to interpret the result.

### Not required for MVP acceptance

The following are explicitly **not required** to declare the basic MVP scientifically usable:

- insertion/deletion calling;
- repeat-aware or poly-C special handling;
- quantitative heteroplasmy;
- mixed-template decomposition;
- sample-level consensus;
- multi-read manifests;
- haplogroup inference or haplogroup-based correction;
- calibrated Phred-like confidence;
- ML inference or training export;
- advanced denoising or baseline correction;
- SCF, VCF/BCF, multi-contig, or genome-scale indexing.

Existing implementations of deferred features do not need to be removed solely because they are outside the MVP. However, they must not block validation of the basic vertical slice, and they must not be presented as release-critical capabilities until separately validated.

Normative SRS requirements for the active MVP must match this scope. Existing code may exceed the MVP, but the roadmap and SRS must not require deferred capabilities merely because they already exist.

### Scientific acceptance order

The project should validate stages in biological dependency order:

```text
1. decoded chromatogram is correct
2. called bases are correct enough to inspect and compare
3. trimming does not discard or retain obvious wrong regions
4. alignment places the read correctly and preserves coordinate identity
5. simple SNVs agree with independently established truth
6. output schema faithfully represents those results
```

Only after this baseline is trustworthy should the project expand to harder event classes or interpretation layers.

### Research notes versus commitments

`docs/TODO.md`, `docs/UPDATE.md`, `docs/tracy_review.md`, and ML sections are research inputs and design notes.

They are not the active product roadmap unless an item is promoted through:

```text
scientific need
  ↓
small requirement
  ↓
ADR when architectural
  ↓
focused implementation
  ↓
tests
  ↓
real-data validation
```

## Consequences

### Positive

- the team can reason about one small scientifically meaningful flow;
- real AB1 validation becomes tractable;
- the output schema can stabilize before advanced features expand it;
- feature count stops being confused with product maturity;
- Tracy and other tools can be studied primarily for biological/methodological correctness rather than as feature checklists.

### Cost

- some implemented functionality may remain experimental even though it works technically;
- exciting research ideas will stay deferred longer;
- the roadmap becomes intentionally less ambitious in the short term.

## Guiding rule

When choosing between adding a new feature and increasing confidence in the current biological core, prefer confidence in the core until the MVP acceptance evidence is complete.


## Development readiness gate

Implementation work may proceed when all of the following are true:

1. the active MVP stages and non-goals are unambiguous;
2. SRS requirements match the MVP scope without requiring deferred features;
3. every stage has a defined input/output boundary and coordinate convention;
4. failure and unresolved states are explicit rather than silently repaired;
5. the public JSON schema represents only claims the MVP is prepared to make;
6. each scientific rule has a validation strategy using synthetic and approved real traces;
7. engineering gates are sufficient to protect the implemented invariants without becoming a feature project of their own.

This gate does **not** require every threshold or algorithmic detail to be known in advance. Those may be refined during focused implementation and real-data validation, provided the stage boundary and biological claim remain stable.
