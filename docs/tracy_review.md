# Lessons from Tracy for Future Signal Development

> Technical design notes for future evolution of `tsuuanmi/signal`, based on architectural and algorithmic lessons from `gear-genomics/tracy`.
>
> This document is not a proposal to port Tracy into Signal. It identifies the parts of Tracy that are scientifically useful for Signal's intended direction, especially mitochondrial DNA Sanger sequencing, and translates them into designs consistent with Signal's existing deterministic, evidence-oriented architecture.

---

# 1. Executive Summary

Signal and Tracy overlap significantly in their low-level Sanger-processing foundations.

Signal already implements equivalents of several important Tracy concepts:

* ABIF/AB1 decoding;
* analyzed A/C/G/T channel extraction;
* PLOC-defined call windows;
* per-channel local peak search;
* strongest-primary calling;
* secondary-peak ratio handling;
* IUPAC ambiguity representation;
* peak-spacing and ambiguity-based quality heuristics;
* adaptive end trimming;
* affine-gap Gotoh alignment;
* forward/reverse orientation selection;
* SNV and small-indel extraction.

Therefore, Signal should **not** spend effort reimplementing Tracy's basic basecaller.

The most important lessons from Tracy are instead higher-level:

1. **Do not collapse the chromatogram to one primary nucleotide too early.**
2. **Represent every locus as an evidence profile that alignment and consensus can consume directly.**
3. **Use profile-to-profile comparison for forward/reverse read agreement.**
4. **Build sample-level consensus from signal evidence rather than primary-call voting.**
5. **Detect persistent post-indel phase shifts using change-point-like signal behavior.**
6. **Evaluate multiple candidate insertion/deletion shifts rather than trusting one alignment gap.**
7. **Filter or downgrade reads before they influence a sample consensus.**
8. **Use Tracy's mixed-indel decomposition as inspiration, but never directly inherit its diploid/heterozygous semantics for mtDNA.**

The recommended architectural direction is:

```text
AB1
 |
 v
ABIF decode
 |
 v
signal-derived peak candidates
 |
 v
locus refinement
 |
 v
LocusEvidence
 |
 +----------------------+----------------------+
 |                      |                      |
 v                      v                      v
primary call      EvidenceProfile       mixed-signal analysis
 |                      |                      |
 |                      v                      |
 |               profile alignment            |
 |                      |                      |
 +----------------------+----------------------+
                        |
                        v
                  ReadObservation
                        |
               +--------+--------+
               |                 |
               v                 v
          forward reads      reverse reads
               |                 |
               +--------+--------+
                        |
                        v
               evidence consensus
                        |
                        v
                 sample-level mtDNA
                        |
         +--------------+---------------+
         |              |               |
         v              v               v
      variants      mixed sites      sample QC
```

The central design principle is:

> **Primary sequence should remain one interpretation of the chromatogram, not the only representation of the chromatogram.**

---

# 2. Scope of This Document

This document focuses on lessons from Tracy that are relevant to Signal's future development.

Primary goals:

* improve signal representation;
* improve alignment robustness;
* improve forward/reverse read reconciliation;
* support multiple reads from one biological sample;
* improve mtDNA indel handling;
* detect mixed-length signal patterns;
* preserve conservative biological semantics;
* retain Signal's deterministic and auditable design.

This document does **not** recommend adopting Tracy wholesale.

Specifically, it does not recommend prioritizing:

* genome-scale FM indexing;
* de novo chromatogram assembly;
* Tracy's diploid heterozygous interpretation;
* unvalidated allelic-fraction estimation;
* SCF support;
* FASTQ output;
* VCF/BCF output;
* Phred-like quality labels without empirical calibration.

---

# 3. Relevant Tracy Architecture

Tracy supports several operations:

```text
chromatogram
    |
    +--> basecalling
    |
    +--> alignment
    |
    +--> decomposition
    |
    +--> consensus
    |
    +--> assembly
    |
    +--> variant calling
```

Relevant source areas include:

```text
src/abif.h
src/profile.h
src/align.h
src/gotoh.h
src/trim.h
src/consensus.h
src/decompose.h
src/assemble.h
```

The strongest lesson is not any individual function.

The important design pattern is:

```text
raw chromatogram
      |
      v
basecall information
      |
      v
continuous nucleotide profile
      |
      v
alignment / comparison / consensus
```

Signal currently performs much of its downstream analysis after reducing the chromatogram to a conservative primary sequence.

That is appropriate for the current MVP, but eventually becomes limiting.

---

# 4. What Signal Already Implements

Before introducing new features, it is important to recognize which Tracy ideas are already present.

## 4.1 Midpoint-Based Call Windows

Signal constructs call windows around PLOC loci using neighboring call positions.

Conceptually:

```text
PLOC[i-1]       PLOC[i]        PLOC[i+1]
     |             |               |
     +------|------+-------|-------+
            ^              ^
        midpoint        midpoint
```

This is already a sensible approach.

There is no strong reason to replace it with Tracy's implementation.

---

## 4.2 Per-Channel Local Peak Search

Signal already searches each A/C/G/T channel independently inside a locus window.

For every channel:

```text
find strongest positive local maximum
```

and if no suitable local maximum exists:

```text
fallback to signal value at PLOC
```

This is conceptually close to Tracy.

No major rewrite is justified solely for Tracy compatibility.

---

## 4.3 Secondary-Peak Ratio

Signal already supports:

```toml
secondary_peak_ratio = 0.33
```

which is also conceptually similar to Tracy's default peak ratio.

In `signal.peak_recall/v3`, this threshold requires both a sufficiently strong selected channel peak and sufficiently strong channel signal at the uniquely strongest primary peak sample. This rejects a remote channel maximum elsewhere in the same PLOC window without claiming that the initial sample-based gate is a complete peak-geometry model.

---

## 4.4 Primary and Ambiguity Calls

Signal already separates:

```text
primary
```

from:

```text
ambiguity
```

Example:

```text
A dominant
G sufficiently strong
```

may produce:

```text
primary   = A
ambiguity = R
```

This is a strong design decision and should be preserved.

---

## 4.5 Relative Quality and End Trimming

Signal already implements a Tracy-like concept of read quality based on:

* local ambiguity;
* call spacing consistency;
* a best section;
* outward trimming.

Signal additionally documents that this score is:

```text
relative_quality
```

and not:

```text
Phred
```

This distinction is important and should remain explicit.

---

## 4.6 Affine-Gap Alignment

Signal already has a deterministic Gotoh implementation with:

* match score;
* mismatch score;
* ambiguous-base score;
* gap-open score;
* gap-extension score;
* semi-global behavior;
* forward/reverse orientation handling;
* circular-reference support.

There is no need to port Tracy's Gotoh implementation.

Future changes should extend the *scoring input*, not replace the core dynamic-programming framework unless benchmarks demonstrate a need.

---

# 5. Window-Wide Peak Limitation and the Initial Signal Fix

The original Signal caller and Tracy share one important problem: each channel may independently choose its strongest local peak anywhere within a locus window.

Example:

```text
call window

       A
      / \
     /   \
----/-----\---------------------------

                     C
                    / \
-------------------/---\--------------
```

Suppose:

```text
A height = 1000
C height = 400
```

and:

```text
secondary_peak_ratio = 0.33
```

Then:

```text
400 / 1000 = 0.40
```

which could produce apparent A/C ambiguity.

But the C peak may actually belong to the neighboring nucleotide event.

This motivates a critical rule:

> **Peak strength alone is insufficient. Secondary peaks must also be spatially compatible with the same nucleotide event.**

`signal.peak_recall/v3` implements the first conservative correction: a secondary channel must pass the ratio using both its selected peak and its signal at the primary peak sample. This removes remote secondary maxima while preserving the uniquely strongest primary, PLOC windows, and existing ambiguity semantics.

A future peak-evidence layer should still replace this one-sample overlap gate with validated peak geometry before profile-based alignment is introduced. Otherwise richer downstream algorithms could propagate secondary evidence that passes at one sample without representing the same complete peak event.

---

# 6. Priority 0: Formalize Locus Evidence

Before introducing Tracy-style profile alignment, Signal should define one stable evidence object per candidate nucleotide locus.

Suggested architecture:

```text
src/
├── peak_detection/
│   ├── mod.rs
│   ├── candidates.rs
│   ├── baseline.rs
│   ├── prominence.rs
│   ├── spacing.rs
│   ├── refinement.rs
│   └── evidence.rs
```

Possible domain type:

```rust
pub struct LocusEvidence {
    pub call_index_0based: usize,

    pub nominal_position_0based: usize,

    pub refined_position_0based: usize,

    pub window_start_0based: usize,

    pub window_end_0based_exclusive: usize,

    pub channels: [ChannelEvidence; 4],

    pub local_spacing: LocalSpacing,

    pub flags: Vec<LocusEvidenceFlag>,
}
```

Per-channel representation:

```rust
pub struct ChannelEvidence {
    pub base: Nucleotide,

    pub peak_position_0based: usize,

    pub raw_height: i32,

    pub baseline: f64,

    pub corrected_height: f64,

    pub noise_sigma: f64,

    pub snr: f64,

    pub prominence: f64,

    pub width_samples: Option<f64>,

    pub offset_from_nominal: i32,

    pub offset_from_refined_locus: i32,

    pub source: PeakSource,
}
```

Possible locus flags:

```rust
pub enum LocusEvidenceFlag {
    Saturated,
    WeakPrimary,
    StrongSecondary,
    MultiPeak,
    CompressedSpacing,
    ExpandedSpacing,
    BaselineShift,
    EdgeAffected,
    NeighborInterference,
}
```

This object would become the stable low-level scientific interface.

---

# 7. Peak Co-Localization

The implemented v3 caller uses channel signal at the primary peak sample as a minimal co-localization gate. Secondary channels should only contribute strongly to future mixed-signal evidence when their complete peak geometry is compatible with the primary event.

A richer future rule could use peak positions and local spacing:

```text
abs(secondary_peak_position - refined_locus_position)
    <= allowed_offset
```

The allowed offset should preferably depend on local spacing.

For example:

```text
allowed_offset =
    max(
        configured_minimum_offset,
        local_expected_spacing * spacing_fraction
    )
```

Possible configuration:

```toml
[peak_detection]

minimum_colocalization_radius_samples = 1

maximum_colocalization_radius_samples = 4

colocalization_spacing_fraction = 0.20
```

Example:

```text
local spacing = 12 samples
fraction      = 0.20

radius ~= 2.4 samples
```

This would generalize the current primary-sample gate and should be introduced only with a versioned, validated locus-evidence method.

---

# 8. Locus Refinement

PLOC should eventually become:

```text
prior position
```

rather than:

```text
absolute locus truth
```

Current conceptual flow:

```text
PLOC
 |
 v
call window
 |
 v
peak comparison
```

Recommended next step:

```text
PLOC
 |
 v
initial event center
 |
 v
local candidate search
 |
 v
refined locus
 |
 v
channel evidence
 |
 v
basecall/profile
```

Refinement should remain tightly bounded.

For example:

```text
candidate_position ∈ current midpoint window
```

and optionally:

```text
abs(candidate_position - PLOC)
    <= configured refinement radius
```

A composite score might combine:

```text
major signal strength
+ peak prominence
+ channel concentration
+ local spacing consistency
- neighbor interference
```

The exact formula should remain versioned and testable.

---

# 9. Priority 0: Evidence Profiles

This is the most important concept to learn from Tracy.

## 9.1 Problem With Early Primary-Sequence Collapse

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

# 10. Evidence Profile Data Model

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

# 11. Building Evidence Weights

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

# 12. Evidence Profile Generation Pipeline

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

# 13. Priority 0: Profile-to-Reference Alignment

Signal currently aligns:

```text
retained primary sequence
```

against:

```text
reference sequence
```

Future Signal should support:

```text
evidence profile
```

against:

```text
reference sequence
```

The current Gotoh framework can remain.

Only the substitution score changes.

---

# 14. Profile-to-Base Scoring

Current canonical scoring resembles:

```text
query A vs reference A -> match_score
query A vs reference G -> mismatch_score
```

With an evidence profile:

```text
A = 0.70
C = 0.05
G = 0.20
T = 0.05
```

against reference `A`, score could be:

```text
0.70 * match(A,A)
+ 0.05 * mismatch(C,A)
+ 0.20 * mismatch(G,A)
+ 0.05 * mismatch(T,A)
```

More generally:

```text
score(profile_i, reference_base) =
    Σ_b weight_i[b] × base_score(b, reference_base)
```

This is similar in spirit to Tracy's profile-aware alignment.

---

# 15. Suggested Interface

Possible abstraction:

```rust
pub trait AlignmentSymbol {
    fn substitution_score(
        &self,
        reference: Nucleotide,
        scoring: &AlignmentScoring,
    ) -> i32;
}
```

or explicit profile scoring:

```rust
pub fn profile_reference_score(
    profile: &EvidenceProfile,
    reference: Nucleotide,
    scoring: &AlignmentScoring,
) -> i32
```

The dynamic-programming engine should not need to understand chromatograms.

It should only consume a deterministic score.

This keeps architecture clean:

```text
signal interpretation
       |
       v
EvidenceProfile
       |
       v
alignment scoring adapter
       |
       v
generic Gotoh
```

---

# 16. Why Profile Alignment Helps mtDNA

Profile-aware alignment is particularly useful for:

* noisy read ends;
* control-region poly-C sequence;
* indel boundaries;
* compressed peaks;
* mixed-base candidates;
* forward/reverse disagreement;
* positions where the primary call is wrong but the correct nucleotide has substantial secondary evidence.

Example:

```text
reference = G

trace evidence:
A = 0.52
G = 0.45
C = 0.02
T = 0.01
```

Primary-only alignment sees:

```text
A vs G
```

and applies a full mismatch penalty.

Profile alignment sees:

```text
strong competing G evidence
```

and can score the position less severely.

This may improve:

```text
orientation selection
alignment placement
gap placement
local indel interpretation
```

---

# 17. Profile Alignment Must Not Hide Poor Signal

A richer profile must not allow poor data to appear artificially compatible with every reference.

For example:

```text
A = 0.25
C = 0.25
G = 0.25
T = 0.25
```

should not become a moderately good match to every base.

Signal should retain an explicit unresolved or uncertainty component.

Possible design:

```rust
pub struct EvidenceProfile {
    pub weights: [f64; 4],
    pub unresolved_weight: f64,
}
```

Then scoring may penalize unresolved evidence separately.

Possible configuration:

```toml
[alignment.profile]

unresolved_score = -1

minimum_informative_weight = 0.60
```

Exact semantics require validation.

---

# 18. Priority 0: Profile-to-Profile Alignment

Tracy also demonstrates the value of comparing two chromatograms as profiles.

This is especially relevant for:

```text
forward read
vs
reverse read
```

from the same amplicon.

Instead of:

```text
forward primary sequence
        vs
reverse primary sequence
```

Signal can eventually compare:

```text
forward evidence profile
        vs
reverse-complement evidence profile
```

---

# 19. Profile-to-Profile Score

Conceptually:

```text
score(profile1, profile2) =
    Σ_i Σ_j
        weight1[i]
        × weight2[j]
        × base_score(i,j)
```

Example:

```text
Forward:
A 0.55
G 0.42

Reverse:
A 0.51
G 0.46
```

Primary sequences may disagree depending on tiny signal differences.

Profile comparison shows that both reads contain nearly identical biological evidence.

This is a much better basis for detecting reproducible mixed signal.

---

# 20. Bidirectional Evidence Interpretation

Consider four cases.

## Case 1 — clean agreement

```text
Forward:
A 0.95
G 0.03

Reverse:
A 0.92
G 0.05
```

Interpretation:

```text
strong bidirectional A support
```

---

## Case 2 — primary disagreement but shared ambiguity

```text
Forward:
A 0.51
G 0.47

Reverse:
A 0.48
G 0.50
```

Primary-only:

```text
Forward -> A
Reverse -> G
```

Profile-aware interpretation:

```text
both support reproducible A/G mixed evidence
```

This should not immediately be labeled heteroplasmy.

Suggested classification:

```text
bidirectionally_reproduced_mixed_signal
```

---

## Case 3 — one noisy read

```text
Forward:
A 0.95
G 0.03

Reverse:
A 0.40
G 0.35
C 0.15
T 0.10
```

Interpretation:

```text
forward strong
reverse low confidence
```

Consensus may still be A while retaining reverse-read uncertainty.

---

## Case 4 — true conflict

```text
Forward:
A 0.95

Reverse:
G 0.94
```

Interpretation:

```text
discordant independent observations
manual review required
```

A majority vote would not solve this safely.

---

# 21. Priority 0: Sample-Level Analysis

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

# 22. Sample-Level Architecture

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

# 23. Explicit Sample Manifest

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

# 24. ReadObservation

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

# 25. PositionObservation

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

# 26. Priority 1: Read Admission

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

# 27. Read Admission Is Not the Same as Variant Filtering

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

# 28. Priority 0: Evidence-Aware Sample Consensus

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

# 29. Consensus Support Level

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

# 30. Consensus Evidence Structure

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

# 31. Priority 1: Mixed-Signal Candidate Detection

Tracy's secondary allele handling is relevant, but Signal should use deliberately conservative terminology.

Preferred:

```text
mixed_base_candidate
```

Avoid until validated:

```text
heteroplasmy
heteroplasmic
allele fraction
minor allele frequency
```

Possible representation:

```rust
pub struct MixedBaseCandidate {
    pub position_1based: usize,

    pub major: Nucleotide,

    pub minor: Nucleotide,

    pub major_evidence: AlleleSignalEvidence,

    pub minor_evidence: AlleleSignalEvidence,

    pub observed_signal_ratio: f64,

    pub support_level: SupportLevel,

    pub classification: MixedSignalClass,
}
```

---

# 32. Mixed-Base Evidence

Useful features include:

```text
major corrected amplitude
minor corrected amplitude

major SNR
minor SNR

minor/major signal ratio

peak offset

co-localization

peak prominence

peak width similarity

baseline stability

local spacing

neighboring peak interference

saturation state

forward recurrence

reverse recurrence

replicate recurrence
```

Example output:

```json
{
  "position": 152,
  "classification": "mixed_base_candidate",
  "major": "A",
  "minor": "G",
  "evidence": {
    "minor_major_ratio": 0.24,
    "major_snr": 21.4,
    "minor_snr": 7.8,
    "peak_offset_samples": 1,
    "co_localized": true,
    "forward_support": 1,
    "reverse_support": 1
  },
  "confidence": "strong"
}
```

This is scientifically useful without claiming:

```text
24% heteroplasmy
```

---

# 33. Priority 1: Learn From Tracy's Indel-Shift Detection

One of Tracy's most interesting features is detection of signal behavior that changes after a candidate indel breakpoint.

The key biological pattern is:

```text
clean signal
clean signal
clean signal
      |
      v
   length mixture
      |
      v
mixed signal
mixed signal
mixed signal
mixed signal
```

For a mixed-length Sanger product, the two molecular populations become phase-shifted after the indel.

This produces persistent downstream double peaks rather than one isolated ambiguous position.

This is particularly important for mtDNA homopolymers and poly-C regions.

---

# 34. Tracy's Breakpoint Concept

Tracy computes a signal-dominance quantity approximately based on:

```text
strongest signal - second strongest signal
```

Clean region:

```text
strongest >> second
```

Mixed region:

```text
strongest closer to second
```

A rolling comparison of upstream and downstream windows is then used to identify a major transition.

Signal should adopt the general concept, but use richer evidence.

---

# 35. Signal Phase-Stability Metrics

Possible per-locus metrics:

```text
dominance =
    major_corrected_height
    - secondary_corrected_height
```

or normalized:

```text
dominance_ratio =
    1 - secondary_corrected_height
        / major_corrected_height
```

Other useful metrics:

```text
profile entropy

secondary SNR

number of co-localized strong channels

peak-spacing residual

local ambiguity rate
```

A combined phase-stability feature could be:

```text
phase_cleanliness(i)
```

where high values represent clear single-phase signal.

---

# 36. Change-Point Detection

Initial deterministic implementation should remain simple and auditable.

For each possible breakpoint:

```text
left_window  = calls [i-W, i)
right_window = calls [i, i+W)
```

Compute:

```text
left_mean_cleanliness

right_mean_cleanliness

delta =
    left_mean_cleanliness
    - right_mean_cleanliness
```

A candidate mixed-length onset should have:

```text
good pre-event signal

large cleanliness drop

persistent poor post-event signal
```

This is stronger evidence than one ambiguous base.

---

# 37. LengthMixtureCandidate

Suggested domain object:

```rust
pub struct LengthMixtureCandidate {
    pub anchor_position_1based: Option<usize>,

    pub onset_call_index_0based: usize,

    pub evidence_span_calls: Range<usize>,

    pub candidate_length_delta: Option<i32>,

    pub pre_event_cleanliness: f64,

    pub post_event_cleanliness: f64,

    pub transition_strength: f64,

    pub support_level: SupportLevel,

    pub confidence: EvidenceClass,
}
```

Initial output should say:

```text
length_mixture_candidate
```

not:

```text
length heteroplasmy
```

unless later validation establishes appropriate assay performance.

---

# 38. Priority 1: Evaluate Candidate Phase Shifts

Tracy does not simply accept the first apparent alignment gap.

It evaluates different insertion/deletion shifts and asks which one best explains downstream signal/reference agreement.

Signal should adopt this principle.

For a breakpoint:

```text
candidate delta ∈ [-N, +N]
```

where:

```text
negative delta = candidate deletion
positive delta = candidate insertion
zero           = no shift
```

For each candidate:

```text
apply proposed phase offset

compare downstream evidence with reference

compute mismatch/error score
```

---

# 39. PhaseShiftHypothesis

Suggested representation:

```rust
pub struct PhaseShiftHypothesis {
    pub delta: i32,

    pub onset_call_index_0based: usize,

    pub downstream_calls_evaluated: usize,

    pub profile_reference_score: f64,

    pub mismatch_count: usize,

    pub unresolved_count: usize,

    pub improvement_over_zero_shift: f64,
}
```

Example:

```text
delta    mismatch
-----------------
-2          34
-1          31
 0          28
+1           6
+2          26
```

Here:

```text
+1
```

is a compelling candidate.

That does not yet prove a biological +1 heteroplasmy event.

It means:

```text
a one-base phase shift explains the downstream mixed signal substantially better
```

which is valuable evidence.

---

# 40. Robust Candidate Selection

Tracy uses median/MAD concepts in parts of its decomposition.

Signal can also use robust statistics.

For candidate error scores:

```text
median_score

MAD =
    median(
        abs(score_i - median_score)
    )
```

A candidate can be considered unusually strong if its fit is substantially better than the typical alternatives.

Possible rule:

```text
candidate_fit
    < median_fit - k * MAD
```

or equivalent score-oriented logic.

Exact cutoffs must be validated empirically.

---

# 41. Do Not Copy Tracy's Diploid Interpretation

Tracy is designed partly around heterozygous nuclear variants.

mtDNA is biologically different.

Signal should never directly translate:

```text
two Tracy alleles
```

into:

```text
two mtDNA haplotypes
```

or:

```text
heteroplasmy percentage
```

without validation.

Possible explanations for mixed Sanger signal include:

```text
true heteroplasmy
PCR artifacts
NUMT amplification
contamination
mixed sample
polymerase slippage
length heterogeneity
poor capillary separation
baseline disturbance
neighbor peak interference
saturation
```

Signal should preserve the evidence while remaining cautious about interpretation.

---

# 42. Poly-C and Homopolymer Context

mtDNA requires explicit repeat-context awareness.

Suggested:

```rust
pub struct SequenceContext {
    pub homopolymer_base: Option<Nucleotide>,

    pub homopolymer_length: usize,

    pub repeat_context: bool,

    pub control_region_poly_c: bool,
}
```

This context should affect:

* review prioritization;
* indel confidence;
* length-mixture interpretation;
* normalization ambiguity;
* consensus state.

It should not automatically suppress variants.

---

# 43. Alignment Stability Around Indels

A normalized indel can look perfectly valid while the underlying alignment placement is unstable.

Repeat context may permit:

```text
placement A
placement B
placement C
```

with nearly identical alignment scores.

Signal should eventually expose:

```text
alignment stability
```

or:

```text
gap-placement ambiguity
```

Possible data:

```rust
pub struct AlignmentStability {
    pub equivalent_placements: usize,

    pub best_score: i32,

    pub alternative_score: Option<i32>,

    pub score_delta: Option<i32>,

    pub repeat_ambiguous: bool,
}
```

This is especially relevant in:

```text
AAAAAA
CCCCCC
```

regions.

---

# 44. Priority 1: Multi-Amplicon mtDNA Consensus

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

# 45. Expected Amplicon Regions

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

# 46. Mapping QC

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

# 47. Whole-Mitogenome Sanger

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

# 48. Consensus Across Amplicons

At a reference position:

```text
amplicon A forward
amplicon A reverse
amplicon B forward
amplicon B reverse
```

may all contribute.

The system should retain independent support counts:

```rust
pub struct SupportSummary {
    pub total_reads: usize,

    pub forward_reads: usize,

    pub reverse_reads: usize,

    pub independent_amplicons: usize,
}
```

A difference seen in:

```text
both directions
and
two independent amplicons
```

should be considered stronger than the same difference seen twice within one forward amplicon.

---

# 49. Profile Consensus Algorithm

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

# 50. Suggested Consensus Policy

Example policy:

## Confirmed canonical

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

## Single-direction canonical

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

## Reproducible mixed signal

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

## High-confidence conflict

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

## Noisy evidence

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

# 51. Variant Calling Should Become Sample-Level

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

    pub support_level: SupportLevel,

    pub consensus_state: ConsensusState,

    pub confidence: EvidenceClass,
}
```

---

# 52. Sample Variant Evidence

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

# 53. Quality Calibration

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

# 54. Future Heteroplasmy Estimation

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

# 55. Assay-Specific Detection Limits

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

# 56. Features From Tracy That Should Not Be Prioritized

## 56.1 FM Index

Tracy supports large-reference genome indexing.

Signal's primary mtDNA reference is approximately:

```text
16.6 kb
```

A genome-scale index is unnecessary.

Prefer:

```text
localized circular affine-gap alignment
```

and later:

```text
banded alignment
```

if performance requires it.

---

# 57. De Novo Assembly

Tracy can perform de novo chromatogram assembly.

For mtDNA, Signal usually knows:

```text
reference = rCRS
```

and often:

```text
expected amplicon
primer
direction
```

Reference-guided placement is simpler and safer.

De novo assembly is therefore low priority.

---

# 58. SCF Input

SCF support may be useful eventually, but it does not significantly improve core mtDNA analysis.

Priority should remain:

```text
AB1 quality
consensus
mixed-signal evidence
indel handling
```

before broadening input formats.

---

# 59. FASTQ Output

Signal currently uses structured JSON as the scientific contract.

FASTQ could eventually be exported from:

```text
primary sequence
+
calibrated quality
```

but until quality is calibrated, FASTQ may imply semantics Signal does not actually support.

Low priority.

---

# 60. VCF/BCF Output

VCF export can be useful for interoperability.

However, it should remain an adapter:

```text
Signal canonical variants
      |
      v
VCF projection
```

rather than making VCF the internal scientific model.

For mtDNA-specific notation, a separate representation layer may be preferable.

---

# 61. Tracy Allelic Fraction

Tracy contains code for estimating allelic proportions from trace signal.

This should **not** be ported directly.

Reasons:

* designed around two-allele assumptions;
* not mtDNA-specific;
* raw channel proportions are not necessarily calibrated mixture fractions;
* sequencing chemistry and base context affect signal amplitude;
* forward and reverse reads may have different response curves.

Signal may study it as a feature-engineering reference only.

---

# 62. Proposed Source Layout

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

# 63. Proposed Stage Versions

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

# 64. Determinism Requirements

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

# 65. Floating-Point Handling

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

# 66. Provenance

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

# 67. Validation Strategy

None of the Tracy-inspired improvements should be considered complete using only synthetic unit tests.

Validation should progress through several levels.

---

# 68. Level 1: Synthetic Unit Tests

Useful for:

```text
peak localization

co-localization

profile normalization

orientation

profile scoring

tie behavior

phase-shift candidate search
```

Examples should isolate one property at a time.

---

# 69. Level 2: Synthetic Chromatogram Shapes

Generate signal arrays containing:

```text
clean single peaks

double peaks

offset neighboring peaks

compressed spacing

baseline drift

saturation

low amplitude

phase shift after insertion

phase shift after deletion
```

This is useful before real biological data is available.

---

# 70. Level 3: Provenanced Real AB1 Corpus

Critical cases:

```text
clean homoplasmic-like mtDNA reads

forward/reverse pairs

poly-C regions

known indels

poor-quality reads

known mixed traces

amplicon overlaps
```

Each file should have:

```text
source

sample identity

assay context

truth status

expected region

direction

reference
```

---

# 71. Level 4: Independent Truth

For claims beyond basic primary-sequence differences, use independent truth where possible.

Examples:

```text
NGS

clonal sequencing

synthetic mixtures

validated reference materials
```

A second call from the same Sanger trace is not independent truth.

---

# 72. Benchmark Against Current Signal

Every new stage should compare against current Signal.

Metrics:

```text
alignment success rate

orientation accuracy

call retention

false ambiguity rate

variant concordance

indel concordance

manual-review burden
```

The new system should not silently degrade clean-read performance.

---

# 73. Benchmark Against Tracy

Tracy can also serve as a reference comparator.

Useful comparison categories:

```text
basecalls

ambiguity calls

trim bounds

orientation

alignment

consensus

mixed-indel candidates
```

The goal is not byte-for-byte compatibility.

The goal is:

```text
understand differences
```

and ensure deviations are intentional.

---

# 74. Suggested Development Order

## Phase A — Peak evidence foundation

Implement:

```text
baseline

corrected height

prominence

local noise

per-channel SNR

spacing-aware co-localization beyond the v3 gate

locus refinement
```

Output:

```text
LocusEvidence
```

Do this first.

---

# 75. Phase B — Evidence profile

Implement:

```text
LocusEvidence
    ->
EvidenceProfile
```

Initially keep:

```text
primary calling unchanged
```

to isolate profile behavior from basecalling behavior.

---

# 76. Phase C — Profile/reference alignment

Add optional:

```text
profile-aware substitution scoring
```

while retaining:

```text
primary-sequence Gotoh
```

as comparison mode.

Benchmark both.

---

# 77. Phase D — ReadObservation

Map each accepted read into:

```text
reference-coordinate observations
```

This becomes the stable sample-analysis input.

---

# 78. Phase E — Two-read consensus

Start with the simplest high-value case:

```text
one forward AB1
+
one reverse AB1
```

Implement:

```text
profile/profile consistency

bidirectional support

discordance

consensus
```

before general N-read assembly.

---

# 79. Phase F — Multi-read sample consensus

Add:

```text
manifest

read admission

multiple amplicons

coverage map

sample consensus

sample variants
```

---

# 80. Phase G — Length-mixture detection

Implement:

```text
signal-cleanliness metric

change-point search

candidate ±N phase shifts

evidence ranking
```

Initially report only:

```text
length_mixture_candidate
```

---

# 81. Phase H — mtDNA-specific interpretation

Add:

```text
poly-C context

repeat context

mtDNA nomenclature projection

haplogroup consistency QC
```

These should remain downstream of generic signal and alignment stages.

---

# 82. Phase I — Calibration

Only after sufficient data:

```text
calibrated call confidence

validated mixed-base detection

validated heteroplasmy estimation
```

---

# 83. ROI Ranking

Recommended priority:

| Priority       | Improvement                             |     Expected ROI |      Effort |
| -------------- | --------------------------------------- | ---------------: | ----------: |
| P0             | Peak geometry beyond the v3 sample gate |        Very high |      Medium |
| P0             | Rich `LocusEvidence`                    |        Very high |      Medium |
| P0             | Evidence profiles                       |        Very high |      Medium |
| P0             | Profile-to-reference alignment          |        Very high |      Medium |
| P0             | Forward/reverse profile consensus       |        Very high | Medium–High |
| P1             | Read admission / sample QC              |             High |  Low–Medium |
| P1             | Sample-level consensus                  |        Very high | Medium–High |
| P1             | Change-point length-mixture detection   |        Very high |      Medium |
| P1             | Candidate ±N phase-shift evaluation     |        Very high |      Medium |
| P1             | Poly-C/repeat context                   |             High |      Medium |
| P2             | Multi-amplicon whole-mtGenome consensus |             High |        High |
| P2             | Alignment-stability evidence            |      Medium–High |      Medium |
| P2             | mtDNA nomenclature layer                |           Medium |      Medium |
| P3             | VCF export                              |       Low–Medium |         Low |
| P3             | FASTQ export                            |              Low |         Low |
| P3             | SCF support                             |              Low |      Medium |
| Skip for mtDNA | FM-index genome alignment               |         Very low |        High |
| Defer          | Quantitative heteroplasmy               | Potentially high |   Very high |

---

# 84. Two Highest-Value Tracy Lessons

If Signal only adopts two major concepts from Tracy, they should be:

## 84.1 Keep nucleotide evidence through alignment

Instead of:

```text
chromatogram
    ->
primary sequence
    ->
alignment
```

move toward:

```text
chromatogram
    ->
LocusEvidence
    ->
EvidenceProfile
    ->
alignment
```

This preserves information Signal already extracts but currently discards from alignment semantics.

---

## 84.2 Model persistent post-indel phase shifts

Instead of treating every indel as:

```text
one gap in one alignment
```

also ask:

```text
Does an insertion/deletion shift explain a persistent change in the downstream chromatogram?
```

This is particularly valuable for:

```text
poly-C regions

homopolymers

length-mixture candidates

mixed mtDNA traces
```

Tracy provides useful algorithmic inspiration for both breakpoint detection and candidate shift testing.

---

# 85. Design Principles to Preserve

While adopting these ideas, Signal should retain its existing strengths.

## Deterministic

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

## Auditable

Every reported result should map back to:

```text
AB1 evidence

call evidence

alignment evidence

sample evidence
```

---

## Conservative

Signal should distinguish:

```text
observation

candidate

supported difference

biological interpretation
```

---

## Typed

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

## Layered

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

# 86. Recommended Final Architecture

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

# 87. Final Recommendation

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

# 88. Tracy Source Areas Worth Keeping as References

When implementing future work, the following Tracy files are particularly useful as conceptual references.

## Basecalling and signal interpretation

```text
src/abif.h
```

Useful for:

```text
peak selection
primary/secondary handling
quality heuristics
```

---

## Trace profiles

```text
src/profile.h
```

Useful for:

```text
representing nucleotide signal as a profile
profile reverse complement
trace/reference profile construction
```

---

## Profile-aware alignment

```text
src/align.h
src/gotoh.h
```

Useful for:

```text
profile-to-sequence scoring
profile-to-profile scoring
affine-gap DP integration
```

Signal should keep its own Gotoh implementation and borrow only the profile-scoring concept.

---

## Forward/reverse consensus

```text
src/consensus.h
```

Useful for:

```text
orientation selection

profile-to-profile alignment

combining evidence

pairwise consensus
```

Avoid directly importing Tracy's quality/genotype terminology.

---

## Mixed-indel decomposition

```text
src/decompose.h
```

Useful for:

```text
change-point-like breakpoint detection

persistent phase-shift detection

candidate insertion/deletion shift evaluation

robust candidate comparison
```

Do not inherit diploid heterozygous assumptions.

---

## Multi-trace assembly

```text
src/assemble.h
```

Useful for:

```text
read admission

orientation handling

multi-read workflow

consensus construction
```

Signal should prefer reference-coordinate mtDNA consensus over directly porting Tracy's progressive assembly.

---

# 89. Decision Summary

Recommended:

```text
YES  LocusEvidence
YES  peak co-localization
YES  locus refinement
YES  evidence profiles
YES  profile/reference alignment
YES  profile/profile comparison
YES  F/R evidence consensus
YES  sample-level read model
YES  read admission
YES  phase-shift change-point detection
YES  candidate ±N shift testing
YES  repeat/poly-C context
YES  multi-amplicon reference-coordinate consensus
```

Defer:

```text
heteroplasmy quantification

calibrated Phred-like confidence

haplogroup-based interpretation
```

Low priority:

```text
SCF

FASTQ

VCF/BCF
```

Avoid for mtDNA-specific core:

```text
FM-index genome search

direct Tracy de novo assembly port

direct diploid decomposition semantics

raw signal ratio = heteroplasmy percentage
```

---

# 90. Closing Principle

The strongest lesson from Tracy can be summarized in one sentence:

> **A Sanger chromatogram contains richer nucleotide evidence than the final primary base string, and Signal should preserve that evidence for as long as possible.**

For mtDNA, the corresponding sample-level principle is:

> **Independent forward, reverse, replicate, and overlapping-amplicon observations should be combined as evidence, not merely as called strings.**

Those two principles should guide the next major architectural evolution of Signal.
