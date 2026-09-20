# ADR-0055: Define the read-local poly-C phase evidence promotion boundary

- **Status:** Accepted
- **Date:** 2026-09-20
- **Implementation:** Boundary implemented by ADR-0056 as continuous internal measurement only; no phase state, weighting, no-call, or public-schema change.

## Context

ADR-0052 establishes that mtDNA evidence observed after an unstable poly-C tract in
sequencing order is directionally lower-confidence than otherwise equivalent evidence that
has not crossed the tract. ADR-0054 separates coherent shifted-reference explainability
from unexplained residual degradation and deliberately keeps the complete candidate curve.

The completed descriptive research surface now includes:

- exact circular read-path poly-C geometry;
- persistent candidate reference-offset curves;
- adjacent-window and distance characterization;
- opposite-orientation same-case controls;
- window/stride/offset sensitivity;
- threshold-free candidate explainability envelopes;
- exact recurrent-locus window membership and per-locus candidate contributions.

These studies support a production design boundary but do not yet justify a production
classifier, confidence multiplier, contribution weight, recovery cutoff, or variant
rejection rule.

The production code currently has a clean one-read boundary:

```text
signal/basecall evidence
        ↓
quality control
        ↓
selected reference alignment
        ↓
primary-sequence variant observation
        ↓
ReadObservation
        ↓
sample reconciliation
```

Sample nucleotide contribution is also intentionally conservative: structural
`NucleotideContribution` eligibility is separate from reliability, and every eligible
profile contributes unit read mass under ADR-0039/ADR-0040.

Promoting the research directly as a `PhaseState` enum or a phase-derived contribution
weight would therefore collapse evidence into interpretation before the required
production thresholds and operating characteristics have been validated.

## Decision

Signal adopts a production **read-local phase evidence boundary** with the rules below.
ADR-0056 implements this boundary as continuous internal measurement only; categorical
interpretation and reliability policy remain deferred.

### 1. Phase evidence is read-local and downstream of selected placement

Production phase measurement MUST run only after one read has independently
selected its reference placement and orientation.

Conceptually:

```text
                       ┌─ primary-sequence variant observation
selected alignment ───┤
                       └─ read-local phase evidence
                                  ↓
                           ReadObservation
```

Phase evidence may consume:

- the selected read orientation and mapped reference path;
- immutable basecall-independent `EvidenceProfile` observations;
- reference sequence context;
- exact sequencing-order tract geometry.

It MUST NOT feed back into alignment scoring, orientation selection, traceback,
canonicalization, source calls, or upstream signal evidence.

### 2. Initial production applicability is rCRS HV1/HV2-specific

The first production method, `signal.polyc_phase/v1`, is scoped to the validated
human rCRS poly-C contexts studied by the current corpus:

- HV2 positions 303–315 with the represented rCRS tract verified;
- HV1 positions 16184–16193 with the represented rCRS tract verified.

Applicability MUST derive from reference identity/context and selected alignment evidence,
not from filename, amplicon label, declared direction, or primer metadata.

An unsupported reference or unverified tract context is **not applicable**. It MUST NOT be
interpreted as phase-stable evidence.

This ADR does not generalize the validated findings to arbitrary homopolymers or arbitrary
references.

### 3. Evidence availability is separate from phase interpretation

Production phase evidence MUST distinguish at least these availability concepts:

```text
not applicable
insufficient evidence
measured evidence
```

They are evidence-availability conditions, not biological or artifact states.

In particular:

```text
no complete downstream phase window
    != stable phase
    != reference support
    != absence of phase instability
```

Profile gaps, read ends, incomplete tract coverage, or otherwise insufficient window
evidence MUST remain explicit rather than being coerced into a clean/stable state.

### 4. Continuous evidence precedes categorical state

Measured phase evidence MUST preserve the scientific dimensions established by ADR-0054
rather than collapsing immediately to one scalar score or categorical state.

The current v1 measurement retains concepts such as:

- tract identity and read-path relationship;
- exact downstream window provenance;
- candidate reference offsets;
- informative-position counts;
- zero-reference mass;
- candidate-shifted reference mass;
- residual mass;
- persistence across consecutive windows.

The complete candidate evidence required by the active method MUST remain available to
the internal scientific model. A later summary MAY derive continuous envelope quantities,
but a winning offset, phase class, or combined phase score requires a separately accepted
and validated interpretation policy.

Therefore this ADR does **not** define `Stable`, `StructuredDephasing`,
`Degraded`, `Recovered`, or similar production states.

### 5. Local reference geometry remains authoritative

A read-level phase hypothesis does not imply that every downstream locus has the same
secondary nucleotide.

For each locus, the expected shifted base is determined by:

```text
candidate reference offset
        +
selected sequencing direction
        +
local reference sequence
```

Positions where the zero-phase and shifted reference bases are identical are
non-informative for that candidate.

Production code MUST NOT replace this geometry with recurrent-locus lookup tables or
hard-coded rules such as "position X becomes base Y."

### 6. Opposite-orientation evidence is corroboration, not detector admission

A usable read MUST remain independently processable.

The phase detector MUST NOT require:

- one forward plus one reverse read;
- one canonical partner;
- pair selection;
- declared acquisition direction.

Opposite-orientation evidence may later provide sample-level corroboration or validation
evidence, but it cannot be a prerequisite for producing read-local phase evidence.

### 7. No production consequence is promoted by this ADR

Phase evidence introduced under this boundary MUST NOT, by itself:

- rewrite primary or ambiguity calls;
- change selected alignment or placement;
- add/remove/normalize variants differently;
- change read or variant eligibility;
- change `NucleotideContribution` structural eligibility;
- change the current unit-mass nucleotide support policy;
- assign confidence attenuation;
- assign a no-call;
- infer genotype, indel, biological length heteroplasmy, contamination, or artifact truth;
- change the current public JSON schemas or strict configuration schema.

A future phase-aware reliability or weighting policy must be a separate accepted decision
and must explicitly supersede or amend the unit-mass contribution contract where needed.

### 8. Validation gate precedes any phase interpretation or weighting

Before any production threshold, categorical phase interpretation, recovery rule,
confidence attenuation, contribution weight, or no-call policy is adopted, the promotion
study MUST document at least:

- the exact corpus and acquisition domain;
- truth/proxy provenance for affected and clean reads;
- source-group-safe development/holdout separation;
- the target false-attenuation objective on clean evidence;
- the threshold/model-selection procedure;
- untouched holdout performance;
- sensitivity to window/stride/offset choices;
- true downstream SNV challenge cases;
- incomplete-window/read-end behavior;
- HV1/HV2 and forward/reverse strata;
- same/cross-amplicon behavior;
- sequencing-run/instrument reproducibility where available;
- known limitations in independent-PCR replication.

A green software test suite or descriptive corpus pattern is not a substitute for this
promotion evidence.

## Ownership and dependency boundary

ADR-0056 implements the intended ownership as:

```text
src/model/phase.rs
    validated read-local phase evidence vocabulary

src/phase/
    pure reference-aware read-local phase measurement

src/pipeline/observation.rs
    orchestration after selected alignment

src/model/read_observation.rs
    owns the measured read-local phase evidence once a real producer exists
```

The phase module depends on validated model/reference evidence. Sample aggregation may
consume read-local phase evidence only after a separate policy decision.

The design specifically excludes putting the detector in:

- `signal_processing`, because the method depends on selected reference orientation;
- `alignment`, because phase evidence must not influence placement;
- `variant_calling`, because phase evidence is not a variant verdict;
- `sample`, because the measurement is read-local and cannot require cross-read pairing.

ADR-0056 supplies the real producer and model types; no placeholder or compatibility path is retained.

## Consequences

- The completed descriptive research is promoted into an explicit production architecture
  boundary without silently promoting a classifier.
- The implemented measurement uses the insertion point after selected alignment and before
  cross-read reconciliation.
- Unsupported references and incomplete evidence remain explicit instead of masquerading
  as stable reads.
- The distinction between structural eligibility and future reliability weighting remains
  intact.
- Local sequence geometry, not recurrent-position heuristics, determines candidate
  shifted-base expectations.
- A future production implementation can be added without changing alignment semantics or
  rewriting the evidence hierarchy.

## Relationship to earlier decisions

- **ADR-0019:** phase measurement is read interpretation over immutable evidence, not a
  biological genotype claim.
- **ADR-0023:** every read remains independently placed before sample reconciliation.
- **ADR-0039:** structural nucleotide contribution eligibility remains unchanged.
- **ADR-0040:** unit-mass nucleotide accumulation remains authoritative until explicitly
  superseded.
- **ADR-0052:** directional post-poly-C reliability remains the intended eventual policy
  direction, while detector/attenuation semantics remain deferred.
- **ADR-0054:** complete candidate evidence and residual explainability remain the
  scientific basis for future measurement.

## Non-goals

This ADR does not define or implement:

- a production phase detector;
- a `PhaseState` enum;
- a winning phase offset;
- detector thresholds;
- a breakpoint or recovery cutoff;
- contribution weighting;
- confidence multipliers;
- no-call behavior;
- variant rejection or artifact classification;
- genotype or length-heteroplasmy inference;
- a configuration key;
- a public output field or schema version.
