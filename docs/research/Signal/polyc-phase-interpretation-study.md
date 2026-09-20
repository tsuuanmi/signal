# Poly-C Phase Interpretation Study

## Purpose

Define the study required before Signal may interpret `signal.polyc_phase/v1`
measurements as a categorical evidence pattern, recovery transition, reliability decision,
contribution weight, no-call, or variant policy.

This is research guidance only. It defines no production state, threshold, configuration,
public output, or sample behavior.

The production authority remains the Rust measurement implemented by ADR-0056:

```text
selected alignment
        ↓
Rust signal.polyc_phase/v1
        ↓
ReadPhaseEvidence
```

Rust/Python measurement parity for the current 89-case corpus is recorded in
[phase-runtime-parity.md](phase-runtime-parity.md). The open question is now
interpretation, not measurement.

## Language boundary

Signal uses the languages for different jobs:

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

A rule discovered in Python is not production behavior until its complete definition and
constants are frozen, implemented in Rust, covered by Rust tests, and validated against the
frozen research evidence.

After promotion, Rust is the single authoritative implementation. Python may remain an
evaluator or parity checker, but not a second independently evolving classifier.

```text
Rust ReadPhaseEvidence
        ↓ validation export
Python development research
        ↓
frozen rule + constants
        ↓
Rust interpretation
        ↓ validation export
Python parity / holdout evaluation
        ↓
Rust remains authoritative
```

## Study question

The first interpretation study asks:

> Can continuous read-local phase evidence distinguish useful observational regimes after
> an rCRS HV1/HV2 poly-C tract without suppressing clean evidence or true downstream
> sequence differences?

It does not attempt to infer:

- biological length heteroplasmy;
- a specific indel length;
- genotype at T310/T16189;
- contamination;
- an artifact mechanism;
- a calibrated probability of correctness.

## Authoritative inputs

Scientific phase measurements come from one completed
`signal.validation_phase_hypotheses/v1` artifact, or equivalent Rust runtime evidence
already proven to match it.

The authoritative measured fields remain:

- read/tract/window identity;
- exact start/end sequencing-order distances;
- exact start/end original call indexes;
- profile-observation count;
- mean profile impurity;
- mean zero-reference mass;
- complete candidate-offset curve;
- informative-position count;
- candidate zero/shifted/residual masses.

Truth, grouping, acquisition, and holdout metadata remain authoritative in
`signal.validation_corpus/v1`.

The study MUST join these existing contracts. It must not add truth or holdout metadata to
the phase-measurement contract merely to make fitting convenient.

## Strict provenance join

Research preparation rejects rather than repairs provenance drift.

Before any row is admitted, verify:

```text
source corpus SHA-256
manifest SHA-256
Signal version
reference SHA-256
configuration SHA-256
validation_case_id
read_sha256
```

Any redundant read metadata carried by the phase artifact, such as amplicon or selected
orientation, must agree with the corpus record.

Do not join by:

- filename;
- declared direction;
- approximate identifiers;
- inferred amplicon;
- a second manifest parser;
- fallback metadata.

Reuse the existing validation corpus/research loader and shared phase-artifact loader.

## Study prerequisites

Threshold/model selection must not start until the local study inputs are frozen.

At minimum:

1. curation decisions are reconciled into the local validation manifest;
2. the manifest SHA-256 is frozen;
3. every `source_group_id` belongs to one study partition;
4. development and locked holdout group names are explicitly declared;
5. `include_in_threshold_fit` is reviewed;
6. clean negative evidence is identified;
7. true downstream SNV challenge evidence is identified;
8. problematic/artifact challenge evidence is identified where available;
9. HV1/HV2 and forward/reverse coverage is summarized;
10. PCR/run/instrument replication limits are documented.

Missing strata are limitations, not permission to treat correlated windows as independent
experiments.

## Interpretation hierarchy

A whole-read phase label is not the primary target.

```text
Read
 └─ tract
     ├─ window 1
     ├─ window 2
     ├─ window 3
     └─ ...
```

One read may be strongly shift-explainable near a tract and later become
reference-coherent. A single read category would erase that transition.

The study therefore treats:

- **window** as the local evidence-pattern unit;
- **ordered windows within one read/tract** as the persistence/recovery unit;
- **read/tract** as a derived summary only;
- **source group** as the independence boundary for development/holdout and uncertainty.

Window count is never an independent sample count.

## Availability is not interpretation

Production already distinguishes:

```text
NotApplicable
Insufficient(reason)
Measured
```

Interpretation applies only to measured evidence unless the endpoint explicitly studies
insufficiency.

These equivalences are invalid:

```text
NotApplicable != clean
Insufficient  != clean
no window     != reference coherent
read end      != recovered
```

A future interpretation type must preserve these distinctions.

## Candidate-wise evidence

For one informative candidate `c`, preserve:

```text
zero(c)
shifted(c)
residual(c)
informative_positions(c)
```

When `shifted(c) + residual(c) > 0`, development research may inspect:

```text
structured_fraction(c)
    = shifted(c) / (shifted(c) + residual(c))
```

This is descriptive only. It is not a probability, confidence, allele fraction, or
calibrated reliability score.

### Informative support

Extreme candidate fractions supported by very few informative positions can be unstable.
`informative_positions` must therefore remain a first-class feature.

A future rule may require minimum informative support, but that value must be chosen on
development data and frozen before holdout evaluation.

Zero-informative candidates retain absent masses. Do not synthesize zeros.

## Candidate envelope and ambiguity

The first study does not require a winning offset.

Repeated sequence can make several offsets similarly explanatory, and a reliability policy
does not need false precision about the exact offset.

Development analysis may inspect:

- maximum candidate-wise structured fraction;
- minimum candidate residual;
- maximum shifted-reference mass;
- candidate spread/separation;
- number of candidates with sufficient informative support.

Do not combine extrema from different candidates into one synthetic "best candidate".

If a future rule uses companion quantities from one selected candidate, all companion
values must come from that same candidate with deterministic tie semantics.

## Research pattern vocabulary

The following names may be used as hypotheses for **measured window evidence**:

```text
reference-coherent
shift-explainable
residual-dominant
indeterminate
```

They are not production enums and make no biological claim.

### Reference-coherent

Hypothesis: zero-phase evidence remains dominant and non-zero evidence does not require a
structured shift explanation.

This must be positively defined; it is not simply "not classified as unstable".

### Shift-explainable

Hypothesis: meaningful non-zero evidence is present, at least one sufficiently informative
candidate explains a substantial fraction as shifted-reference mass, and residual evidence
remains limited enough for a structured interpretation.

This does not prove an indel or length heteroplasmy.

### Residual-dominant

Hypothesis: meaningful non-zero evidence is present but tested shifts leave substantial
residual evidence.

This does not prove artifact or unusability.

### Indeterminate

Hypothesis: measured evidence is insufficiently discriminatory because of weak signal, too
few informative positions, ambiguous candidates, or a development-defined uncertainty
region.

Indeterminate evidence remains explicit rather than being forced into another category.

## Truth discipline

Signal output is not independent truth for its own interpretation study.

Do not use these as biological ground truth:

- `interrupt_aligned_base`;
- phase impurity;
- shifted-reference mass;
- residual mass;
- a candidate selected from the same evidence;
- Signal variant calls;
- labels derived from the tested phase features.

Observed interrupt base is valid for stratification and challenge analysis only.

Any affected/clean performance label must retain independent truth or explicit proxy
provenance. Proxy-labelled performance must be reported as proxy performance rather than
biological sensitivity/specificity.

## Safety objectives

Before feature or threshold search, declare a maximum tolerated false attenuation/no-call
rate on clean evidence.

The numeric objective belongs to the frozen local study plan, not this generic research
document.

True downstream SNVs are a co-primary safety challenge. A phase policy is unacceptable if
it improves apparent handling of problematic poly-C reads by suppressing independently
true downstream differences.

Report clean and true-SNV challenge behavior separately.

## Development and holdout

All evidence from one independent source group remains on one side of the split.

Development data may be used to choose:

- feature family;
- informative-position gate;
- thresholds;
- ambiguity/separation rule;
- persistence rule;
- recovery rule.

Holdout phase measurements remain untouched until the complete rule and constants are
frozen.

A research preparation step should expose development measurements plus aggregate
holdout/readiness counts, not holdout phase feature tables.

`holdout_group` is a manifest string, not a hard-coded two-value enum. The study declares
which group names are development, holdout, excluded, or unassigned. Unknown groups never
silently enter fitting.

`include_in_threshold_fit=false` excludes a case from development fitting even when its
holdout group is otherwise development.

## Pseudo-replication

Overlapping windows from one trace are correlated.

Every report must include counts for:

```text
windows
read/tracts
reads
PCR replicates
source groups
sequencing runs / instruments when available
```

Resampling and confidence intervals must respect the highest relevant independent grouping
level. Window-wise bootstrap is not evidence for independent performance.

## Persistence

A local window pattern is not automatically a tract-level interpretation.

Evaluate ordered adjacent windows from the same read/tract. A future rule may require
multiple compatible consecutive windows, but the required count and any tolerated
indeterminate transition must be chosen on development data.

Persistence uses source window identity/order. It must not regenerate windows or candidate
evidence.

## Recovery

Recovery is an evidence transition, not a fixed distance cutoff.

Invalid:

```text
distance >= X
    => recovered
```

Candidate form:

```text
previously non-reference-coherent evidence
        ↓
transition
        ↓
multiple consecutive reference-coherent windows
        ↓
candidate recovery
```

Evaluate:

- number of supporting windows;
- intervening indeterminate windows;
- read ends near apparent recovery;
- profile gaps;
- HV1 versus HV2;
- forward versus reverse.

Distance may be descriptive but cannot establish recovery by itself.

## Production measurement constants

The primary interpretation study consumes the frozen production
`signal.polyc_phase/v1` method:

```text
25 profile-bearing observations per window
stride 5 profile-bearing observations
candidate offsets -5..-1 and +1..+5
```

Existing sensitivity research may test whether conclusions are fragile to reasonable
measurement choices, but fitting must not silently redefine these production constants.

A different measurement method requires a separately versioned measurement change.

## QC evidence

Noisy-region membership, quality, SNR, signal intensity, and trace-integrity evidence may
stratify results and explain failures.

They do not automatically become phase-state inputs.

Adding one to a future rule requires development evidence that it improves the declared
objective without circularly using a QC verdict as phase truth.

## Exact local membership before weighting

`PhaseWindowEvidence` retains exact window bounds and call-index bounds, but windows are
built from profile-bearing observations only; missing-profile observations are skipped.

Therefore interval containment:

```text
window start distance <= locus <= window end distance
```

does not prove that the locus was a measured window member.

The recurrent-locus research path already reconstructs exact membership and rejects
interval-only membership.

Any future locus-local attenuation, weighting, or no-call implementation must preserve or
derive exact **Rust-side** membership/projection before applying interpretation to a locus.
It must not map state to loci by interval containment alone.

This is a future weighting prerequisite, not a reason to change the already validated
measurement in this research step.

## Python research tooling

Future study-preparation code remains outside the production scientific core:

```text
completed validation corpus
        +
completed phase evidence
        ↓
strict provenance join
        ↓
development-only research tables
        +
partition/readiness counts
```

The Python research layer must:

- reuse the validated corpus loader;
- reuse the shared phase-artifact loader;
- never recompute phase windows or candidate masses;
- avoid a second manifest parser;
- avoid exposing holdout phase measurements before rule freeze;
- hash-bind source/output artifacts;
- publish without overwrite;
- remain local validation/research tooling.

It is disposable research infrastructure, not production scientific authority.

## Rust promotion boundary

If the evidence justifies interpretation, the frozen rule should become a focused Rust
module, conceptually:

```text
src/phase/
├── geometry.rs
├── measure.rs
└── interpret.rs
```

with a pure boundary:

```text
ReadPhaseEvidence
        ↓
phase::interpret
        ↓
ReadPhaseInterpretation
```

A promoted interpreter should:

- consume validated read-local phase evidence only;
- contain the frozen rule and constants;
- perform no filesystem access;
- load no Python artifact;
- read no validation manifest;
- require no paired/opposite-orientation read;
- not mutate alignment, calls, variants, or source evidence;
- return typed Rust interpretation data.

Its PR must include Rust types/tests, method documentation, accepted ADR/SRS changes, and
the required `docs/src` mirror.

## Interpretation is not weighting

A successful interpretation does not automatically imply a contribution weight.

Keep the dependency boundary:

```text
ReadPhaseEvidence
        ↓
ReadPhaseInterpretation
        ↓
separate reliability/contribution policy
```

Any weighting/no-call policy must independently satisfy
`docs/validation/polyc-phase-promotion.md` and explicitly amend ADR-0040 / the current
unit-read-mass contract.

Do not expose an uncalibrated `0.0..1.0` value named `confidence` or `probability`.

## Rust validation after promotion

After implementing the frozen rule in Rust, validation should mirror the successful
measurement-parity workflow:

```text
frozen development rule/spec
        ↓
Rust interpretation
        ↓
validation-only serialization
        ↓
Python parity / holdout evaluation
```

Categorical/structural fields compare exactly. Retained derived floating-point quantities
use an explicit documented tolerance.

Validation tooling must not reimplement phase measurement geometry as a fallback.

After parity, Rust remains authoritative; duplicated Python classification logic should not
continue as a parallel production definition.

## Reporting

Development and holdout reports include at minimum:

- corpus/manifest/reference/configuration identities;
- frozen rule version;
- source-group/PCR/run/instrument counts;
- read, read/tract, and window counts;
- availability counts;
- interpretation counts;
- clean false attenuation/no-call;
- affected/proxy challenge performance;
- true downstream SNV retention;
- HV1/HV2 results;
- forward/reverse results;
- same/cross-amplicon results where available;
- insufficient/read-end/profile-gap behavior;
- reviewed failure cases and limitations.

Aggregate window accuracy alone is not an acceptable performance claim.

## Promotion gates

Production interpretation remains blocked until:

1. corpus and curation state are frozen;
2. source-group development/holdout partitions are frozen;
3. study and safety objectives are predeclared;
4. rule selection uses development data only;
5. rule/constants are frozen before holdout inspection;
6. holdout results satisfy the predeclared objective;
7. true downstream SNVs do not show unacceptable suppression;
8. tract/orientation/amplicon and available replicate strata are reviewed;
9. incomplete evidence/read-end behavior is explicit;
10. the frozen rule is implemented in Rust;
11. Rust behavior is validated against the frozen research evidence;
12. ADR/SRS/method/source documentation explicitly promotes the behavior.

Weighting/no-call remains separately blocked even if interpretation passes.

## Delivery order

```text
1. freeze this study design
2. verify/freeze local corpus and partitions
3. build development-only Python research join/readiness tooling
4. explore/falsify candidate rules on development data
5. freeze one rule and all constants
6. evaluate untouched holdout
7. if justified, implement the rule in Rust
8. export and parity-check Rust interpretation
9. only then study sample reliability/weighting
```

This sequence keeps Python exploratory and Rust authoritative.

## Non-goals

This study does not:

- add production source;
- add a production `PhaseState`;
- choose a winning offset;
- choose numeric thresholds;
- define a recovery distance;
- change `signal.polyc_phase/v1`;
- change configuration or public schemas;
- alter variant or nucleotide-contribution eligibility;
- alter unit-mass sample support;
- infer length heteroplasmy, genotype, artifact, or contamination;
- make Python part of the runtime scientific core.
