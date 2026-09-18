# Sample-Level Analysis and Consensus

## 21. Priority 0: Sample-Level Analysis

Tracy's consensus and assembly commands reinforce an important architectural lesson:

> Sanger analysis should eventually operate on a biological sample containing multiple traces, not only independent AB1 files.

Signal's existing one-trace pipeline should remain stable:

```text
one AB1
  ->
one read-level result
```

A new layer should add:

```text
one biological sample
  ->
multiple read-level observations
  ->
sample-level consensus
```

---

## 22. Sample-Level Architecture

Recommended architecture:

```text
sample manifest
      |
      v
manifest validation
      |
      +-----------------------------+
      |             |               |
      v             v               v
    AB1 #1        AB1 #2          AB1 #N
      |             |               |
      v             v               v
read pipeline   read pipeline   read pipeline
      |             |               |
      +-------------+---------------+
                    |
                    v
             ReadObservations
                    |
                    v
          sample evidence model
                    |
            +-------+-------+
            |               |
            v               v
        consensus        discordance
            |               |
            +-------+-------+
                    |
                    v
              sample variants
                    |
                    v
               sample QC
```

---

## 23. Explicit Sample Manifest

Biological relationships should not be inferred purely from filenames.

Example:

```yaml
schema_version: 1

sample:
  id: SAMPLE_001

reference:
  name: rCRS

reads:
  - id: HV1_F
    trace: SAMPLE_001_HV1_F.ab1
    amplicon: HV1
    direction: forward
    primer: L15997
    expected_region:
      start: 15950
      end: 16450

  - id: HV1_R
    trace: SAMPLE_001_HV1_R.ab1
    amplicon: HV1
    direction: reverse
    primer: H16401
    expected_region:
      start: 15950
      end: 16450
```

Manifest provenance should become part of sample-level reproducibility.

---

## 24. ReadObservation

Each processed read should produce an internal representation suitable for aggregation.

Suggested model:

```rust
pub struct ReadObservation {
    pub read_id: String,

    pub trace_sha256: String,

    pub orientation: Orientation,

    pub amplicon: Option<String>,

    pub expected_region: Option<ReferenceRegion>,

    pub mapped_segments: Vec<ReferenceSegment>,

    pub positions: Vec<PositionObservation>,

    pub indels: Vec<ReadIndelObservation>,

    pub quality: ReadQualitySummary,

    pub admission: ReadAdmission,
}
```

---

## 25. PositionObservation

Suggested representation:

```rust
pub struct PositionObservation {
    pub reference_position_1based: usize,

    pub call_index_0based: usize,

    pub primary: char,

    pub ambiguity: char,

    pub profile: EvidenceProfile,

    pub evidence: CallEvidenceSummary,

    pub alignment_state: AlignmentState,
}
```

This should be the bridge between:

```text
read-level signal
```

and:

```text
sample-level consensus
```

---

## 26. Priority 1: Read Admission

Tracy's assembly workflow excludes traces that do not align sufficiently well before they influence consensus.

Signal should adopt the same general idea.

Suggested state:

```rust
pub enum ReadAdmission {
    Accepted,
    AcceptedWithWarnings,
    Rejected,
}
```

Possible reasons:

```rust
pub enum ReadAdmissionReason {
    LowCallableIdentity,
    InsufficientOverlap,
    PoorSignal,
    ExcessiveAmbiguity,
    UnexpectedAmplicon,
    UnexpectedOrientation,
    OutsideExpectedRegion,
    AmbiguousPlacement,
    InsufficientRetainedBases,
    ExcessiveNoisyRegions,
}
```

A rejected trace should remain represented in the sample result with the reason.

It should simply not influence consensus.

---

## 27. Read Admission Is Not the Same as Variant Filtering

These concepts must remain separate.

Read admission:

```text
Should this entire read participate in sample-level evidence aggregation?
```

Variant filtering:

```text
Should this specific candidate difference be reported?
```

A usable read may contain a local low-quality variant candidate.

Conversely, a globally poor read may contain a visually strong local peak but still be unsuitable as independent confirmation.

---

## 28. Priority 0: Evidence-Aware Sample Consensus

Consensus must not be a simple nucleotide majority vote.

Bad:

```text
A
A
G

=> A
```

Better:

```text
A high-confidence forward
A high-confidence reverse
G low-confidence noisy forward

=> A
   bidirectionally confirmed
   minor discordance retained
```

Suggested state:

```rust
pub enum ConsensusState {
    Confirmed,
    SingleDirection,
    SingleRead,
    Discordant,
    MixedCandidate,
    LowConfidence,
    NoCoverage,
}
```

Consensus nucleotide:

```rust
pub enum ConsensusBase {
    Canonical(Nucleotide),
    Ambiguous(char),
    NoCall,
}
```

These should remain separate concepts.

---

## 29. Consensus Support Level

Suggested independent-evidence hierarchy:

```rust
pub enum SupportLevel {
    SingleRead,
    SameDirectionReplicate,
    Bidirectional,
    IndependentAmplicon,
}
```

A position supported by:

```text
forward + reverse
```

should generally have stronger evidence than:

```text
two forward reads
```

because the latter may share direction-specific artifacts.

Independent amplicons may be stronger still.

---

## 30. Consensus Evidence Structure

Possible internal representation:

```rust
pub struct PositionConsensus {
    pub position_1based: usize,

    pub base: ConsensusBase,

    pub state: ConsensusState,

    pub support_level: SupportLevel,

    pub support: [f64; 4],

    pub observations: Vec<ReadPositionSupport>,

    pub flags: Vec<ConsensusFlag>,
}
```

Compact output might summarize:

```json
{
  "position": 73,
  "base": "A",
  "state": "confirmed",
  "support_level": "bidirectional",
  "observations": {
    "total": 3,
    "forward": 2,
    "reverse": 1
  }
}
```

Full low-level evidence can remain internal or available in a separate research/debug format.

---
