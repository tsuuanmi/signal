# Multi-Amplicon mtDNA Consensus and Variant Evidence

## 44. Priority 1: Multi-Amplicon mtDNA Consensus

Tracy supports multi-trace assembly.

Signal can learn from the workflow without copying the progressive MSA implementation.

For mtDNA, reference-guided coordinate aggregation is simpler and more appropriate.

Recommended:

```text
trace 1
   |
   v
rCRS placement
   |
   +--------------------+
                        |
trace 2                 |
   |                    |
   v                    |
rCRS placement          |
   |                    |
   +--------------------+
                        |
trace N                 |
   |                    |
   v                    |
rCRS placement          |
   |                    |
   +--------------------+
                        |
                        v
            reference-coordinate observations
                        |
                        v
                  sample consensus
```

This avoids unnecessary de novo MSA complexity.

---

## 45. Expected Amplicon Regions

If the manifest provides an expected region, Signal should use it.

Instead of:

```text
align each read against all 16,569 bases
```

prefer:

```text
expected region
      |
      v
region + margin
      |
      v
localized circular slice
      |
      v
alignment
```

Example:

```text
expected:
16000..16450

margin:
100 bp

search:
15900..16550
```

with circular projection as needed.

Benefits:

* faster alignment;
* lower false-placement risk;
* better QC;
* easier detection of wrong amplicons.

---

## 46. Mapping QC

Possible warnings:

```text
mapped_outside_expected_region

unexpected_orientation

low_overlap

low_identity

ambiguous_placement

origin_wrap_unexpected

expected_primer_context_absent
```

Possible object:

```rust
pub struct MappingQc {
    pub expected_region_match: bool,

    pub expected_orientation_match: bool,

    pub placement_unique: bool,

    pub warnings: Vec<MappingWarning>,
}
```

---

## 47. Whole-Mitogenome Sanger

Whole-mitogenome support is not achieved simply by changing:

```toml
regions = [[1, 16569]]
```

It requires:

```text
multiple amplicons

explicit sample manifest

overlap handling

coverage map

read admission

cross-amplicon consensus

coverage gaps

conflict detection

sample-level publication
```

Recommended profile:

```toml
[mtdna]

profile = "whole-mitogenome"
```

but implementation should only claim whole-mitogenome support once the sample-level pipeline exists.

---

## 48. Consensus Across Amplicons

At a reference position, reads from any overlapping amplicons may contribute:

```text
HV1F
HV1R
HV2F
HV3R
```

The important property is not a pre-built F/R pair. It is the topology of the
actual observations covering that coordinate.

Retain factorized support:

```rust
pub struct SupportSummary {
    pub total_reads: usize,
    pub forward_reads: usize,
    pub reverse_reads: usize,
    pub amplicons: usize,
    pub technical_replicate_groups: usize,
}
```

Do not use `independent_amplicons` as a default biological claim. Different
amplicons/primers can reduce shared artifacts, but independence depends on assay
design.

A cross-amplicon overlap such as HV2F + HV3R is first-class evidence even if
HV2R or HV3F is absent.

---

## 49. Profile Consensus Algorithm

A simple first implementation can sum weighted profile evidence.

For each reference coordinate:

```text
support_A = Σ observation_weight × profile_A
support_C = Σ observation_weight × profile_C
support_G = Σ observation_weight × profile_G
support_T = Σ observation_weight × profile_T
```

Observation weight may depend on:

```text
read admission
local call evidence
strand
alignment confidence
noise state
```

It should initially remain interpretable and deterministic.

Avoid opaque nonlinear confidence logic before a validation corpus exists.

---

## 50. Suggested Consensus Policy

Example policy:

### Confirmed canonical

```text
one nucleotide dominates strongly

AND

support comes from both directions
```

Result:

```text
Confirmed
```

---

### Single-direction canonical

```text
one nucleotide dominates strongly

BUT

only one sequencing direction contributes
```

Result:

```text
SingleDirection
```

---

### Reproducible mixed signal

```text
same two nucleotides have significant evidence

AND

pattern repeats across forward/reverse reads
```

Result:

```text
MixedCandidate
```

---

### High-confidence conflict

```text
forward strongly supports A

reverse strongly supports G
```

Result:

```text
Discordant
```

not:

```text
choose majority
```

---

### Noisy evidence

```text
support distribution broad

low SNR

or insufficient information
```

Result:

```text
LowConfidence
```

or:

```text
NoCall
```

---

## 51. Variant Calling Should Become Sample-Level

Current read-level variant semantics:

```text
This trace differs from the reference.
```

Future sample-level variant semantics:

```text
The aggregated sample evidence supports a difference from the reference.
```

These must remain different domain types.

Suggested:

```rust
pub struct ReadVariant {
    // current-style read-level difference
}
```

and:

```rust
pub struct SampleVariant {
    pub canonical: CanonicalVariant,

    pub observations: Vec<VariantObservation>,

    pub support: SupportTopology,

    pub consensus_state: ConsensusState,

    pub confidence: EvidenceClass,
}
```

---

## 52. Sample Variant Evidence

Example:

```json
{
  "position": 73,
  "reference": "A",
  "alternate": "G",
  "support": {
    "level": "bidirectional",
    "forward_reads": 1,
    "reverse_reads": 1,
    "independent_amplicons": 1
  },
  "confidence": "strong"
}
```

Signal should avoid calling this:

```text
homoplasmic
```

unless future sample-level inference explicitly supports that conclusion.

---

## 53. Quality Calibration

Tracy computes estimated quality values, and Signal computes relative quality.

Signal should preserve its current conservative terminology.

Current:

```text
relative_quality
phred_calibrated = false
```

Future improvement should target:

```text
P(call is incorrect | signal evidence)
```

Only after empirical calibration.

Possible future object:

```rust
pub struct CalibratedCallConfidence {
    pub probability_correct: f64,

    pub model_id: String,

    pub model_sha256: String,

    pub calibrated: bool,
}
```

Calibration metrics should include:

```text
Brier score

log loss

reliability curves

expected calibration error

error rate vs retained yield
```

---

## 54. Future Heteroplasmy Estimation

Signal should not estimate heteroplasmy fraction directly from:

```text
minor peak / major peak
```

Raw peak ratio is not automatically biological mixture fraction.

A proper future workflow requires known mixtures:

```text
0%
2.5%
5%
10%
15%
20%
30%
40%
50%
```

and ideally multiple:

```text
base substitutions

sequence contexts

instruments

runs

directions
```

Then:

```text
signal features
      |
      v
calibration model
      |
      v
estimated fraction
      |
      v
uncertainty
```

---

## 55. Assay-Specific Detection Limits

Any quantitative heteroplasmy result should be tied to validated:

```text
LoB
Limit of Blank

LoD
Limit of Detection

LoQ
Limit of Quantification
```

Possible provenance:

```json
{
  "method": "signal.sanger-mixture/v1",
  "validated_lod": 0.12,
  "validated_loq": 0.18,
  "model_sha256": "..."
}
```

Until such validation exists, Signal should report:

```text
mixed signal evidence
```

rather than quantitative heteroplasmy.

---


---

## 56. Do Not Build Amplicon Consensus First

For tiled mtDNA, avoid:

~~~text
amplicon 1 reads -> amplicon 1 consensus
amplicon 2 reads -> amplicon 2 consensus
then merge consensuses
~~~

That hierarchy loses original read evidence before cross-amplicon overlaps are
evaluated.

Prefer:

~~~text
all traces
 -> independent ReadObservation values
 -> reference-coordinate/event aggregation
 -> sample interpretation
~~~

Amplicon identity remains attached to each contribution, so the final sample
model can distinguish same-amplicon F/R support from cross-amplicon overlap.

---

## 57. Consensus Sequence and Sample Variant Are Sibling Projections

From the authoritative sample evidence:

~~~text
SampleEvidence
   +--> SampleVariant[]
   +--> ConsensusState[]
   +--> Coverage/QC
   +--> optional consensus FASTA-like sequence
~~~

The consensus string should not sit upstream of sample variant calling.
