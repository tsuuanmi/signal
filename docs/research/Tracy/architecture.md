# Tracy-Informed Research Architecture

This document mirrors the role of root `docs/architecture.md` for Tracy-informed research. It is non-normative until a decision is promoted into root Signal documentation and source.

## 62. Proposed Source Layout

A future Signal source tree could evolve toward:

```text
src/
├── trace/
│
├── basecalling/
│
├── peak_detection/
│   ├── mod.rs
│   ├── candidates.rs
│   ├── baseline.rs
│   ├── prominence.rs
│   ├── refinement.rs
│   ├── colocalization.rs
│   └── evidence.rs
│
├── evidence_profile/
│   ├── mod.rs
│   ├── build.rs
│   └── scoring.rs
│
├── signal_processing/
│
├── quality_control/
│
├── alignment/
│   ├── gotoh.rs
│   ├── profile.rs
│   ├── orient.rs
│   └── traceback.rs
│
├── mixed_signal/
│   ├── mod.rs
│   ├── point.rs
│   ├── change_point.rs
│   ├── phase_shift.rs
│   └── evidence.rs
│
├── sample/
│   ├── mod.rs
│   ├── manifest.rs
│   ├── observation.rs
│   ├── admission.rs
│   ├── consensus.rs
│   ├── support.rs
│   └── qc.rs
│
├── mtdna/
│   ├── mod.rs
│   ├── profiles.rs
│   ├── context.rs
│   ├── nomenclature.rs
│   └── haplogroup.rs
│
└── variant_calling/
```

The exact structure is optional.

The important separation is:

```text
signal evidence

≠

alignment

≠

sample consensus

≠

biological interpretation
```

---

## 63. Proposed Stage Versions

Signal should continue versioning scientific algorithms.

Possible future stages:

```text
signal.peak_evidence/v1

signal.evidence_profile/v1

signal.profile_gotoh/v1

signal.read_observation/v1

signal.sample_consensus/v1

signal.mixed_base_candidate/v1

signal.length_mixture_candidate/v1

signal.phase_shift_hypothesis/v1

signal.sample_variant/v1
```

Each version should define:

* input;
* output;
* mathematical behavior;
* tie-breaking;
* thresholds;
* failure conditions.

---

## 64. Determinism Requirements

All new algorithms should preserve Signal's deterministic behavior.

Avoid:

```text
unordered iteration affecting output

random initialization

floating-point platform divergence where avoidable

undocumented tie resolution
```

Explicitly define:

```text
channel tie order

candidate ordering

orientation tie behavior

phase-shift tie behavior

consensus tie behavior
```

Example:

```text
A < C < G < T
```

may remain a deterministic technical tie-breaker without implying biological preference.

---

## 65. Floating-Point Handling

Profile alignment introduces more floating-point arithmetic.

To preserve reproducibility, consider:

```text
fixed-point evidence weights
```

or:

```text
rounded deterministic scores
```

Example:

```rust
const PROFILE_SCALE: i32 = 10_000;
```

Convert:

```text
0.7234
```

to:

```text
7234
```

before DP scoring.

This may improve cross-platform determinism.

Whether it is necessary should be tested.

---

## 66. Provenance

Future sample-level results should record identities for:

```text
all AB1 inputs

manifest

configuration

reference

Signal version

peak-evidence method

profile method

alignment method

consensus method

mixed-signal method

optional calibration model

optional mtDNA nomenclature version

optional haplogroup tree/version
```

Example:

```json
{
  "methods": {
    "peak_evidence": "signal.peak_evidence/v1",
    "profile": "signal.evidence_profile/v1",
    "alignment": "signal.profile_gotoh/v1",
    "consensus": "signal.sample_consensus/v1"
  }
}
```

---

## 85. Design Principles to Preserve

While adopting these ideas, Signal should retain its existing strengths.

### Deterministic

```text
same inputs
+
same config
+
same software
=
same scientific result
```

---

### Auditable

Every reported result should map back to:

```text
AB1 evidence

call evidence

alignment evidence

sample evidence
```

---

### Conservative

Signal should distinguish:

```text
observation

candidate

supported difference

biological interpretation
```

---

### Typed

Prefer:

```rust
LocusEvidence

EvidenceProfile

ReadObservation

MixedBaseCandidate

LengthMixtureCandidate

SampleVariant
```

rather than loosely structured maps.

---

### Layered

Do not put:

```text
mtDNA nomenclature
```

inside:

```text
low-level alignment
```

Do not put:

```text
heteroplasmy interpretation
```

inside:

```text
peak detection
```

Each layer should have one scientific responsibility.

---

## 86. Recommended Final Architecture

Long-term:

```text
                              AB1
                               |
                               v
                       strict ABIF decode
                               |
                               v
                       peak candidate search
                               |
                               v
                         locus refinement
                               |
                               v
                    +-----------------------+
                    |     LocusEvidence     |
                    |-----------------------|
                    | corrected amplitude   |
                    | baseline              |
                    | SNR                   |
                    | prominence            |
                    | co-localization       |
                    | spacing               |
                    | peak geometry         |
                    +-----------+-----------+
                                |
                   +------------+-------------+
                   |                          |
                   v                          v
              primary call              EvidenceProfile
                   |                          |
                   |                          v
                   |                  profile alignment
                   |                          |
                   +------------+-------------+
                                |
                                v
                         ReadObservation
                                |
                +---------------+---------------+
                |                               |
                v                               v
           point mixed                     phase-shift
           evidence                        detection
                |                               |
                v                               v
       MixedBaseCandidate            LengthMixtureCandidate
                |                               |
                +---------------+---------------+
                                |
                                v
                         sample manifest
                                |
                                v
                +---------------+---------------+
                |                               |
                v                               v
          forward reads                    reverse reads
                |                               |
                +---------------+---------------+
                                |
                                v
                    evidence-aware consensus
                                |
                                v
                        sample-level mtDNA
                                |
           +--------------------+--------------------+
           |                    |                    |
           v                    v                    v
        variants            mixed sites         coverage/QC
           |                    |                    |
           +--------------------+--------------------+
                                |
                                v
                        mtDNA context layer
                                |
                  +-------------+-------------+
                  |                           |
                  v                           v
            nomenclature                haplogroup QC
```

---

## 87. Final Recommendation

Signal should treat Tracy as:

```text
a source of proven algorithmic ideas
```

not:

```text
a compatibility target
```

The basic Tracy-style Sanger basecalling concepts are already present in Signal.

The next generation of Signal should instead improve on Tracy by combining:

```text
Tracy-style profile-aware processing

+

Signal's stricter typing

+

Signal's deterministic scientific contracts

+

robust signal evidence

+

explicit mtDNA semantics

+

sample-level bidirectional consensus
```

The most important conceptual transition is:

```text
OLD

AB1
 ->
primary sequence
 ->
reference difference
```

to:

```text
FUTURE

AB1
 ->
signal evidence
 ->
read observation
 ->
multi-read evidence
 ->
sample consensus
 ->
mtDNA interpretation
```

That shift is substantially more important than adding more file formats, more CLI commands, or a more sophisticated basecaller in isolation.

---
