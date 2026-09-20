# Poly-C Phase Interpretation Study

## Purpose

Define the research and validation plan required before Signal may interpret
`signal.polyc_phase/v1` measurements as a categorical evidence pattern, recovery
transition, reliability decision, contribution weight, no-call, or variant policy.

This document is research-only. It does not define production behavior, thresholds,
configuration, public output, or a `PhaseState` type.

The current production authority remains the Rust measurement implemented by
ADR-0056:

```text
selected alignment
        ↓
Rust signal.polyc_phase/v1
        ↓
ReadPhaseEvidence
```

The completed Rust/Python measurement-parity evidence is recorded in
[phase-runtime-parity.md](phase-runtime-parity.md). The open scientific question is now
interpretation, not window/candidate measurement.

## Language and implementation boundary

Signal uses different languages for different responsibilities:

```text
Rust
    production scientific authority
    typed invariants
    deterministic runtime behavior

Python
    local research
    exploratory statistics
    corpus joins
    visualization
    falsification
    validation/parity tooling
```

Python MUST NOT become a runtime dependency of the scientific core.

A future interpretation rule discovered with Python is not production behavior until the
rule and all constants are frozen, independently implemented in Rust, covered by Rust
tests, and validated against the frozen research evidence.

After promotion, Rust is the single authoritative interpretation implementation. Python
may remain as an evaluator or parity checker, but MUST NOT remain a second authoritative
classifier with independently evolving semantics.

Conceptually:

```text
Rust ReadPhaseEvidence
        ↓ validation export
Python development research
        ↓
frozen rule + constants
        ↓
Rust phase interpretation
        ↓ validation export
Python parity / holdout evaluation
        ↓
Rust remains authoritative
```

## Study question

The first interpretation study asks:

> Can the continuous read-local phase evidence reliably distinguish useful observational
> regimes after an rCRS HV1/HV2 poly-C tract without erasing clean evidence or true
> downstream sequence differences?

The study does not ask whether the trace proves:

- biological length heteroplasmy;
- a specific indel length;
- genotype at T310/T16189;
- contamination;
- an artifact mechanism;
- a calibrated probability of correctness.

Those are stronger claims than the current evidence supports.

## Current authoritative inputs

The study consumes only completed, provenance-matched validation artifacts.

Primary scientific input:

```text
signal.validation_phase_hypotheses/v1
```

or an equivalent Rust validation export proven to match
`signal.validation_phase_runtime/v1`.

The authoritative phase quantities are:

- exact read/tract/window identity;
- exact start/end sequencing-order distances;
- exact original call-index bounds;
- profile-observation count;
- mean profile impurity;
- mean zero-reference mass;
- complete candidate-offset curve;
- candidate informative-position count;
- candidate zero-reference mass;
- candidate shifted-reference mass;
- candidate residual mass.

Validation grouping and truth/proxy metadata remain authoritative in:

```text
signal.validation_corpus/v1
```

The interpretation study MUST join phase evidence back to the validated corpus rather
than adding truth, holdout, or acquisition metadata to the phase-measurement contract.

## Provenance join

A research join MUST reject rather than repair provenance drift.

Before any study row is admitted, the following identities must agree:

```text
source corpus SHA-256
manifest SHA-256
Signal version
reference SHA-256
configuration SHA-256
validation_case_id
read_sha256
```

Where phase evidence carries redundant read metadata such as amplicon or selected
orientation, the joined corpus/read record must agree exactly.

The join MUST NOT use:

- filename matching;
- declared acquisition direction as placement;
- approximate case names;
- fallback manifest parsing;
- inferred amplicon membership.

The existing validation corpus/research loaders remain the authority for corpus metadata.
A phase-interpretation research layer must reuse them rather than creating a second
manifest parser or grouping model.

## Study prerequisites

Threshold/model selection must not start until the local validation corpus has been
reviewed and frozen for this study.

At minimum:

1. curation decisions have been reconciled into the local validation manifest;
2. the manifest SHA-256 is frozen for the study;
3. each `source_group_id` belongs to exactly one study partition;
4. development and locked holdout group names are explicitly declared;
5. `include_in_threshold_fit` has been reviewed;
6. clean negative evidence is present;
7. true downstream SNV challenge evidence is identified;
8. artifact/problematic-trace challenge evidence is identified where available;
9. HV1/HV2 and forward/reverse coverage is summarized;
10. PCR/run/instrument replication limits are documented.

If a required stratum is absent, the study records that as a limitation rather than
silently treating correlated windows as independent evidence.

## Unit of interpretation

A whole-read phase label is not the primary study target.

The current evidence is naturally hierarchical:

```text
Read
 └─ tract
     ├─ window 1
     ├─ window 2
     ├─ window 3
     └─ ...
```

One read can show strong shifted-reference explainability immediately after a tract and
later return to reference-coherent evidence. A single read-level category would collapse
that transition.

The study therefore treats:

- the **window** as the local evidence-pattern unit;
- the ordered **window sequence within one read/tract** as the persistence/recovery unit;
- the **read/tract** as a derived summary level only;
- the **source group** as the primary independence boundary for development/holdout and
  statistical uncertainty.

Window counts MUST NOT be reported as independent sample counts.

## Evidence availability remains separate

The production availability vocabulary is already explicit:

```text
NotApplicable
Insufficient(reason)
Measured
```

Interpretation research applies only to measured evidence unless a study endpoint
explicitly concerns insufficiency.

The following remain invalid equivalences:

```text
NotApplicable != clean
Insufficient  != clean
no window     != reference coherent
read end      != recovered
```

No future interpretation enum may erase these distinctions.

## Candidate-wise quantities

For one informative candidate offset `c`, define descriptive quantities only after
preserving the source candidate identity:

```text
zero(c)
shifted(c)
residual(c)
informative_positions(c)
```

When `shifted(c) + residual(c) > 0`, development analysis may inspect:

```text
structured_fraction(c)
    = shifted(c) / (shifted(c) + residual(c))
```

This value is descriptive. It is not a probability, confidence value, allele fraction,
or calibrated reliability score.

### Informative evidence gate

A candidate with very few informative positions can show an extreme mass fraction by
chance or local sequence repetition. Therefore interpretation research MUST preserve
`informative_positions` as a first-class dimension.

A future rule may require minimum informative support, but that minimum must be selected
and frozen on development data before holdout evaluation.

Zero-informative candidates remain explicit missing numeric evidence and must never receive
synthetic zero values.

## Candidate envelope without false precision

The first interpretation study does not require a winning offset.

Repeated sequence can make multiple offsets similarly explanatory. Selecting one offset
when several provide nearly equivalent evidence would create false precision that is not
required for a reliability policy.

Development analysis may inspect candidate-envelope quantities such as:

- maximum candidate-wise structured fraction;
- minimum candidate residual;
- maximum shifted-reference mass;
- spread/separation across candidate values;
- number of candidates with sufficient informative support.

However, quantities from different candidates MUST NOT be combined and described as one
synthetic "best candidate".

For example, this is invalid:

```text
shifted mass from candidate A
+
residual mass from candidate B
=
best candidate
```

If a future rule requires companion quantities from one selected candidate, they must be
taken from that same candidate with deterministic tie semantics.

## Candidate observational regimes

The following names are allowed as research hypotheses for **measured window evidence**:

```text
reference-coherent
shift-explainable
residual-dominant
indeterminate
```

They are not production enums and are intentionally observational rather than biological.

### Reference-coherent

Hypothesis:

- zero-phase evidence remains dominant;
- non-zero evidence is limited;
- no tested shift provides substantial structured evidence requiring interpretation.

This state must not be defined merely as "not classified as unstable".

### Shift-explainable

Hypothesis:

- meaningful non-zero evidence is present;
- at least one sufficiently informative candidate explains a substantial fraction as
  shifted-reference mass;
- residual mass remains low enough that a simple candidate shift remains informative.

This does not prove an indel or length heteroplasmy.

### Residual-dominant

Hypothesis:

- meaningful non-zero evidence is present;
- tested candidate shifts leave substantial residual evidence;
- no sufficiently supported candidate explains the window cleanly enough for the proposed
  structured interpretation.

This does not prove artifact or unusability.

### Indeterminate

Hypothesis:

- evidence is measured but insufficiently discriminatory for the proposed interpretation;
- examples include weak non-zero evidence, too few informative positions, ambiguous
  candidate structure, or a development-defined uncertainty region.

Indeterminate evidence must remain explicit rather than being coerced into a clean or
problematic category.

## Labels and truth discipline

Signal output is not an independent truth source for its own interpretation study.

In particular, the following MUST NOT be used as biological ground truth:

- observed `interrupt_aligned_base`;
- high phase impurity;
- shifted-reference mass;
- residual mass;
- a candidate offset selected from the same evidence;
- existing Signal variant calls;
- research envelope labels derived from the tested metrics.

Observed interrupt base may be used for stratification and challenge analysis only.

Any affected/clean label used for performance claims must document independent truth or an
explicitly weaker proxy provenance. Proxy-labelled results must be reported as proxy
performance rather than biological sensitivity/specificity.

## Clean evidence and true-SNV safety objective

Before threshold/model search, the study must declare a maximum acceptable
false-attenuation or false-no-call objective on clean evidence.

A numeric objective is deliberately not chosen in this research design document; it must
be predeclared with the frozen local study plan before development fitting.

True downstream SNVs are a co-primary safety challenge. A phase rule is unacceptable if
it gains apparent performance on problematic poly-C reads by suppressing independent true
sequence differences.

The study must therefore report clean and true-SNV challenge behavior separately.

## Development and holdout discipline

All related evidence from one independent source group remains on one side of the
development/holdout boundary.

Development data may be used to choose:

- candidate feature family;
- informative-position gate;
- interpretation thresholds;
- ambiguity/separation rule;
- persistence requirement;
- recovery rule.

Locked holdout data may not be inspected for phase metrics while these choices are being
made.

A research preparation step should expose development phase measurements and only aggregate
holdout/readiness counts until the rule is frozen.

`holdout_group` is a manifest string, not a hard-coded two-value enum. The study must
explicitly declare which group names mean development, holdout, excluded, or unassigned.
An unknown/unassigned group must never silently enter fitting data.

`include_in_threshold_fit=false` must exclude that case from development fitting even
when its holdout-group name otherwise belongs to development.

## Avoiding pseudo-replication

Overlapping windows from one trace are strongly correlated.

Every research report must provide counts at multiple levels:

```text
windows
read/tracts
reads
PCR replicates
source groups
sequencing runs / instruments when available
```

Confidence intervals or resampling used for validation must respect the highest relevant
independent grouping level. Window-wise bootstrap/resampling is not valid evidence for
independent performance.

## Persistence

A local window pattern is not automatically a tract-level interpretation.

The study must evaluate ordered adjacent windows from the same read/tract and quantify
whether a proposed regime persists.

A future persistence rule may require multiple consecutive compatible windows, but the
number of windows and any tolerated transition/ambiguity must be selected on development
data and frozen before holdout evaluation.

Persistence must use source window order and exact window identity. It must not reconstruct
alternate windows or candidate evidence.

## Recovery

Recovery is an evidence transition, not a fixed genomic-distance cutoff.

Invalid rule:

```text
distance >= X
    => recovered
```

Candidate study form:

```text
previously non-reference-coherent evidence
        ↓
transition
        ↓
multiple consecutive reference-coherent windows
        ↓
candidate recovery
```

The study must evaluate:

- number of supporting consecutive windows;
- intervening indeterminate windows;
- read ends near the apparent recovery;
- profile gaps;
- HV1 versus HV2;
- forward versus reverse orientation.

Distance from the tract may be reported descriptively but cannot by itself establish
recovery.

## Method constants

The production measurement method is already frozen as
`signal.polyc_phase/v1`:

```text
25 profile-bearing observations per window
stride 5 profile-bearing observations
candidate offsets -5..-1 and +1..+5
```

Interpretation research uses the authoritative v1 measurement for the primary study.

Existing parameter-sensitivity research may be used to assess whether the qualitative
conclusions are fragile to reasonable measurement choices, but interpretation fitting
must not silently redefine the production measurement constants.

If a different measurement method is eventually required, it is a separately versioned
measurement change rather than an interpretation threshold tweak.

## Noisy regions and other QC evidence

Noisy-region membership, quality, SNR, signal intensity, and trace-integrity evidence may
be used to stratify performance and investigate failures.

They must not automatically become phase-state inputs.

Adding one of those dimensions to a future interpretation rule requires explicit
development evidence and validation that it improves the intended operating objective
without circularly reusing an existing QC verdict as phase truth.

## Exact local membership before weighting

The current `PhaseWindowEvidence` preserves exact window bounds and call-index bounds,
but windows are constructed from profile-bearing observations only. Missing-profile
observations are skipped.

Therefore an interval such as:

```text
window start distance .. window end distance
```

does not prove that every locus in that interval was a member of the measured window.

The recurrent-locus research path already reconstructs exact membership from the
authoritative window generator and explicitly rejects interval-only membership.

Any future **locus-local** attenuation, weighting, or no-call implementation must preserve
or derive exact Rust-side membership/projection before applying a window interpretation to
a locus. It MUST NOT map state to loci by start/end interval containment alone.

This is a production-weighting prerequisite, not a reason to alter the current validated
measurement in this research-only step.

## Research tooling design

A future development-data preparation tool should remain outside the Rust production core.

Its responsibility is limited to:

```text
completed validation corpus
        +
completed phase hypothesis/runtime evidence
        ↓
strict provenance join
        ↓
development-only research tables
        +
partition/readiness counts
```

It must:

- reuse the current validated corpus loader;
- reuse the shared phase-artifact loader;
- avoid recomputing phase windows or candidate masses;
- avoid a second manifest parser;
- avoid exposing holdout phase measurements before rule freeze;
- hash-bind its sources and outputs;
- publish without overwrite;
- remain local/ignored validation data.

This Python tooling is a research convenience, not the scientific runtime implementation.

## Rust promotion architecture

If development and holdout evidence justify an interpretation, the frozen rule should be
implemented as a focused Rust phase module, conceptually:

```text
src/phase/
├── geometry.rs
├── measure.rs
└── interpret.rs
```

with a pure boundary such as:

```text
ReadPhaseEvidence
        ↓
phase::interpret
        ↓
ReadPhaseInterpretation
```

The interpretation module should:

- consume only validated read-local phase evidence;
- contain the frozen rule and method constants;
- perform no filesystem access;
- load no Python artifact;
- read no validation manifest;
- require no paired/opposite-orientation read;
- not mutate alignment, calls, variants, or source evidence;
- return typed Rust interpretation data.

A production interpretation PR must add the corresponding Rust types, focused unit tests,
method documentation, accepted ADR/SRS changes, and `docs/src` ownership mirror.

## Interpretation is not weighting

A successful Rust interpretation must not automatically return or apply a sample
contribution weight.

Keep the dependency boundary:

```text
ReadPhaseEvidence
        ↓
ReadPhaseInterpretation
        ↓
separate future reliability/contribution policy
```

A weighting/no-call policy must independently satisfy the promotion protocol and explicitly
amend ADR-0040 / the current unit-read-mass sample contribution contract.

The interpretation type should not use an uncalibrated `0.0..1.0` value named
`confidence` or `probability` unless a separate calibration study justifies those
semantics.

## Rust validation after promotion

Once a frozen interpretation is implemented in Rust, validation should mirror the proven
measurement-parity pattern:

```text
frozen development rule/spec
        ↓
Rust interpretation
        ↓
validation-only serialization
        ↓
Python parity / holdout evaluation
```

Structural interpretation fields should compare exactly.

Any retained derived floating-point quantities must compare under an explicit documented
numeric tolerance.

The validation layer must not reimplement phase measurement geometry as a fallback.

## Reporting

Development and holdout reports must include, at minimum:

- exact corpus/manifest/reference/configuration identities;
- exact frozen rule version;
- source-group count;
- PCR replicate count;
- run/instrument count when available;
- read and read/tract counts;
- window counts;
- evidence-availability counts;
- interpretation counts;
- clean false attenuation/no-call;
- affected/proxy challenge performance;
- true downstream SNV retention;
- HV1/HV2 results;
- forward/reverse results;
- same/cross-amplicon results where available;
- insufficient/read-end/profile-gap behavior;
- identified failure cases and limitations.

Aggregate window accuracy alone is not an acceptable performance claim.

## Promotion gates

Production interpretation remains blocked until all of the following are true:

1. the local corpus and curation state are frozen;
2. development/holdout source groups are frozen;
3. the study objective and safety objective are predeclared;
4. candidate feature/rule selection is performed on development data only;
5. the complete rule and constants are frozen before holdout inspection;
6. holdout results satisfy the predeclared objective;
7. true downstream SNV challenges do not show unacceptable suppression;
8. tract/orientation/amplicon and available replicate strata are reviewed;
9. incomplete evidence and read-end behavior are explicit;
10. the frozen rule is implemented in Rust;
11. Rust behavior is validated against the frozen research rule/evidence;
12. the production ADR/SRS/method/source/docs changes explicitly authorize the behavior.

Weighting/no-call remains separately blocked even if interpretation passes.

## Proposed implementation sequence

The dependency-aware delivery order is:

```text
1. freeze this study design
2. verify/freeze local corpus and partitions
3. build development-only research join/readiness tooling in Python
4. explore and falsify candidate interpretation rules on development data
5. freeze one rule and all constants
6. evaluate the untouched holdout
7. if justified, implement the frozen interpretation in Rust
8. export and parity-check Rust interpretation
9. only then study a separate sample reliability/weighting policy
```

This order preserves one production authority and avoids turning exploratory Python code
into a permanent parallel scientific implementation.

## Explicit non-goals

This study design does not:

- add production source code;
- add a `PhaseState` enum;
- choose a candidate offset;
- choose numeric thresholds;
- define a recovery distance;
- change `signal.polyc_phase/v1`;
- change configuration;
- change public schemas;
- alter variant eligibility;
- alter nucleotide contribution eligibility;
- alter unit-mass sample support;
- infer length heteroplasmy, genotype, artifact, or contamination;
- make Python part of the runtime scientific core.
