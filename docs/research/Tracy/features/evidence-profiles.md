# Evidence Profiles

## 9. Priority 0: Evidence Profiles

This is the most important concept to learn from Tracy.

### 9.1 Problem With Early Primary-Sequence Collapse

Consider this signal:

```text
A = 1000
G = 450
C = 40
T = 30
```

A primary caller may represent the site as:

```text
primary   = A
ambiguity = R
```

But when downstream alignment consumes only:

```text
A
```

information is lost.

The chromatogram actually says:

```text
A strongly supported
G moderately supported
C/T almost unsupported
```

The downstream aligner should be able to use this information.

---

## 10. Evidence Profile Data Model

Signal should derive one normalized evidence profile per locus.

For example:

```rust
pub struct EvidenceProfile {
    pub weights: [f64; 4],

    pub unresolved_weight: f64,

    pub primary: char,

    pub ambiguity: char,

    pub calibrated: bool,

    pub method: EvidenceProfileMethod,
}
```

Important:

```text
weights
```

should initially be called:

```text
evidence weights
```

not:

```text
probabilities
```

unless they have actually been calibrated.

A possible profile:

```text
A = 0.72
C = 0.02
G = 0.24
T = 0.02
```

This means:

```text
relative evidence distribution
```

not:

```text
72% biological allele fraction
```

and not:

```text
72% probability that the base is A
```

without validation.

---

## 11. Building Evidence Weights

Tracy uses a relatively simple trace profile.

Signal can do better by using its planned signal evidence.

A future profile could combine:

```text
baseline-corrected peak height
peak SNR
peak prominence
co-localization
peak width
local spacing compatibility
saturation state
local-noise state
```

One possible interim deterministic formulation:

```text
channel_score =
    corrected_height
    × snr_factor
    × colocalization_factor
    × prominence_factor
```

Then:

```text
weight[channel] =
    channel_score
    / sum(channel_scores)
```

The exact formula should not be finalized without real trace validation.

The initial goal is merely to create a stable interface so that the profile-generation algorithm can evolve later.

---

## 12. Evidence Profile Generation Pipeline

Recommended pipeline:

```text
raw analyzed channels
        |
        v
peak candidates
        |
        v
baseline correction
        |
        v
noise estimation
        |
        v
prominence estimation
        |
        v
co-localization filtering
        |
        v
locus refinement
        |
        v
LocusEvidence
        |
        v
EvidenceProfile
        |
   +----+----+
   |         |
   v         v
basecall   alignment
```

The primary sequence remains useful.

It should simply cease to be the only representation consumed downstream.

---
