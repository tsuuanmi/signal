# Signal mtDNA Processing Improvement Plan

> Detailed technical roadmap for evolving `tsuuanmi/signal` from a deterministic single-trace Sanger analyzer into an evidence-aware mitochondrial DNA analysis pipeline while preserving the project's current architectural strengths.

---

## 1. Executive Summary

Signal currently provides a strong deterministic foundation for Sanger ABIF/AB1 processing:

```text
AB1
 |
 v
ABIF decode
 |
 v
signal-derived re-calling at PLOC loci
 |
 v
rolling signal-quality analysis
 |
 v
relative quality control + end trimming
 |
 v
forward/reverse alignment against reference
 |
 v
primary-sequence SNV/indel extraction
 |
 v
compact auditable JSON
```

The current design already handles several mtDNA-specific concerns correctly:

* rCRS support;
* circular-reference alignment;
* origin wrapping across `16569 -> 1`;
* forward/reverse read orientation;
* normalized SNVs and small indels;
* explicit distinction between a primary-sequence difference and a genotype;
* explicit refusal to infer heteroplasmy from insufficient evidence;
* deterministic algorithms and deterministic scientific outputs;
* provenance through checksums and versioned output contracts;
* strict parsing and resource limits;
* separation between scientific stages and filesystem/reporting concerns.

However, the core biological abstraction remains:

```text
one electropherogram
    ->
one primary sequence
    ->
differences versus one reference
```

For practical mtDNA analysis, especially Sanger sequencing of HVR regions or whole mitochondrial genomes, the desired abstraction should become:

```text
one biological sample
    ->
multiple electropherograms
    ->
multiple independent signal observations
    ->
evidence-aware consensus
    ->
mtDNA-specific variant interpretation
    ->
mixed-signal / heteroplasmy evidence
    ->
sample-level QC
```

The most important improvements are therefore not cosmetic CLI changes or additional output formats.

The recommended priority is:

1. improve peak/locus evidence;
2. add sample-level multi-read consensus;
3. replace raw-height/read-relative thresholds with calibrated or normalized evidence;
4. add bidirectional confirmation;
5. add mtDNA-specific indel/poly-C handling;
6. add mixed-base evidence without prematurely calling heteroplasmy;
7. add haplogroup-based QC;
8. validate against a real truth corpus;
9. only then introduce ML-based confidence or heteroplasmy estimation.

---

# 2. Current Architecture

The current scientific pipeline can be represented as:

```text
AB1 + configuration
        |
        v
+-------------------+
|     ABIF decode   |
+-------------------+
        |
        v
+-------------------+
|    basecalling    |
| PLOC-based loci   |
+-------------------+
        |
        v
+-------------------+
| signal processing |
| rolling local SNR |
+-------------------+
        |
        v
+-------------------+
| quality control   |
| relative quality  |
| end-only trimming |
+-------------------+
        |
        +----------------------+
        |                      |
        | basecall             | analyze
        |                      |
        v                      v
 basecalls JSON          reference loading
                               |
                               v
                        +---------------+
                        |   alignment   |
                        | forward/rev   |
                        | circular ref  |
                        +---------------+
                               |
                               v
                        +---------------+
                        |variant calling|
                        +---------------+
                               |
                               v
                        analysis JSON
```

This architecture should largely be preserved.

The recommended evolution is to add new layers rather than rewrite the existing pipeline.

---

# 3. Architectural Principles to Preserve

The following characteristics of Signal should remain first-class requirements.

## 3.1 Determinism

Given identical:

* AB1 bytes;
* configuration;
* reference;
* algorithm version;

Signal should continue to produce identical scientific results.

Any future ML component must therefore have:

* explicit model identity;
* explicit model checksum;
* deterministic inference where practical;
* versioned feature definitions;
* reproducible preprocessing.

---

## 3.2 Immutable Scientific Stage Outputs

Scientific stages should continue to consume validated typed values and return new typed values.

Avoid:

```rust
fn process(trace: &mut Chromatogram)
```

Prefer:

```rust
fn process(trace: &Chromatogram) -> Result<ProcessedTrace>
```

Decoded signal arrays should remain immutable source evidence.

Any smoothing, correction, denoising, normalization, or baseline adjustment should produce a separate representation.

---

## 3.3 Provenance

Every scientifically meaningful result should remain reproducible from recorded provenance.

At minimum retain identities for:

```text
input AB1
configuration
reference
Signal version
algorithm version
optional feature definition
optional ML model
haplogroup tree/version
nomenclature rules
```

---

## 3.4 Conservative Biological Semantics

Signal should not use labels such as:

```text
heteroplasmy
pathogenic
genotype
homoplasmy
contamination
```

unless the relevant analysis has enough validated evidence to justify the term.

Intermediate states should instead use terminology such as:

```text
mixed_base_candidate
secondary_signal
primary_sequence_difference
discordant_read
low_confidence_consensus
review_required
```

---

# 4. Key Scientific Limitation: PLOC Is Still the Locus Authority

Current basecalling is signal-derived only after vendor-defined loci have already been accepted.

Conceptually:

```text
ABIF vendor processing
        |
        v
      PLOC
        |
        v
Signal call window
        |
        v
A/C/G/T peak comparison
```

Signal therefore currently answers:

> Which nucleotide appears strongest near this vendor-provided locus?

It does not fully answer:

> Where are the nucleotide events in the chromatogram?

That distinction becomes important for:

* compressed peaks;
* poor vendor placement;
* missed bases;
* duplicate base positions;
* insertions;
* deletions;
* homopolymers;
* poly-C regions;
* length heteroplasmy;
* noisy read ends.

---

# 5. P0: Introduce Explicit Peak Evidence

A new peak-evidence representation should be introduced before significantly expanding mtDNA interpretation.

Suggested source layout:

```text
src/
├── peak_detection/
│   ├── mod.rs
│   ├── baseline.rs
│   ├── candidates.rs
│   ├── locus.rs
│   ├── metrics.rs
│   └── evidence.rs
```

The existing basecalling module can consume this evidence.

---

## 5.1 Current Problem

The existing logic approximately performs:

```text
for each PLOC call window:
    find highest A peak anywhere in window
    find highest C peak anywhere in window
    find highest G peak anywhere in window
    find highest T peak anywhere in window

    compare heights
```

This can create false ambiguity.

Example:

```text
window:

           A
           /\
          /  \
---------/----\---------------------

                         C
                         /\
------------------------/--\--------

```

Suppose:

```text
A peak = 1000
C peak = 400
```

The ratio is:

```text
400 / 1000 = 0.40
```

With:

```toml
secondary_peak_ratio = 0.33
```

the site could be interpreted as an A/C mixed call even though the C peak belongs to a neighboring nucleotide event.

---

# 6. Peak Co-localization

Secondary alleles should only be considered meaningful when they are spatially compatible with the primary event.

Suggested rule:

```text
major_peak_position = p

secondary signal is locus-compatible only when:

abs(secondary_peak_position - p) <= allowed_offset
```

The allowed offset should not necessarily be one fixed number.

Possible formulation:

```text
allowed_offset =
    max(
        configured_minimum_offset,
        local_spacing * configured_spacing_fraction
    )
```

For example:

```text
local_spacing = 12 samples
spacing_fraction = 0.20

allowed_offset ~= 2-3 samples
```

---

# 7. Proposed Peak Evidence Data Model

Example:

```rust
pub struct LocusEvidence {
    pub locus_index: usize,

    pub nominal_position_0based: usize,

    pub refined_position_0based: usize,

    pub call_window_start_0based: usize,

    pub call_window_end_0based_exclusive: usize,

    pub channels: [ChannelEvidence; 4],

    pub local_spacing: LocalSpacing,

    pub flags: Vec<LocusEvidenceFlag>,
}
```

Channel evidence:

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

Spacing:

```rust
pub struct LocalSpacing {
    pub previous: Option<usize>,
    pub next: Option<usize>,
    pub expected: Option<f64>,
}
```

Flags:

```rust
pub enum LocusEvidenceFlag {
    Saturated,
    CompressedSpacing,
    ExpandedSpacing,
    WeakPrimary,
    StrongSecondary,
    MultiPeak,
    BaselineShift,
    EdgeAffected,
}
```

---

# 8. Peak Prominence

Peak height alone is not sufficient.

Example:

```text
baseline = 900
peak     = 1050

raw height:
1050

actual signal above baseline:
150
```

Compare with:

```text
baseline = 100
peak     = 700

corrected signal:
600
```

Raw peak height incorrectly favors the first situation.

A better metric is:

```text
corrected_height = peak_height - local_baseline
```

and ideally:

```text
prominence =
    peak_height -
    max(local_left_valley, local_right_valley)
```

Both should be retained as evidence.

---

# 9. Signal-to-Noise Should Become a Per-Locus Primitive

The existing rolling SNR analysis is useful, but future basecalling should also expose local per-channel signal quality.

For a channel:

```text
baseline = robust local baseline estimate

noise_sigma =
    robust estimate of background variation

signal =
    max(0, peak - baseline)

snr =
    signal / max(noise_sigma, noise_floor)
```

This value should be stored at the locus/channel level.

It should not necessarily become an immediate hard threshold.

Instead it should become one feature in a larger confidence calculation.

---

# 10. PLOC Should Become a Prior Instead of Ground Truth

Recommended evolution:

### Current

```text
PLOC
 |
 v
fixed locus
 |
 v
call
```

### Next generation

```text
PLOC
 |
 v
initial locus estimate
 |
 v
local signal candidate search
 |
 v
position refinement
 |
 v
locus evidence
 |
 v
call
```

### Later

```text
vendor PLOC candidates
        +
signal-derived peak candidates
        |
        v
spacing-aware locus inference
        |
        v
final event sequence
```

This progression preserves backwards compatibility while gradually reducing dependence on vendor base locations.

---

# 11. Optional Locus Refinement

For each nominal PLOC `p`, search a small region:

```text
[p - radius, p + radius]
```

Determine whether a nearby composite signal maximum provides a better event center.

One possible composite score:

```text
composite(position) =
    max_A(position)
  + max_C(position)
  + max_G(position)
  + max_T(position)
```

A better future version may combine:

```text
signal strength
peak shape
neighbor spacing
previous event position
next event expectation
```

Do not allow arbitrary position movement.

The refined position should remain bounded by:

```text
neighboring midpoint window
```

or another explicit geometry constraint.

---

# 12. P0: Replace Raw Peak Thresholding as Primary Variant Evidence

The current default includes a raw threshold similar to:

```toml
minimum_peak_height = 150
```

Raw fluorescence intensity is unlikely to be portable across:

* instruments;
* capillaries;
* runs;
* chemistry;
* signal scaling;
* maintenance state;
* injected DNA concentration.

It may remain useful as:

```text
instrument sanity threshold
```

but should not be the primary biological evidence threshold.

---

# 13. Use a Multi-dimensional Evidence Vector

For each call:

```text
CallEvidence = {
    major_corrected_height,
    major_snr,
    secondary_corrected_height,
    secondary_snr,
    secondary_major_ratio,
    peak_prominence,
    peak_colocalization,
    peak_spacing,
    local_baseline,
    local_noise,
    saturation_flag,
    noisy_window_membership,
    optional_vendor_quality,
    strand_confirmation,
    replicate_confirmation
}
```

Variant confidence should ultimately be derived from these features rather than:

```text
raw maximum peak >= X
AND
relative read score > Y
```

---

# 14. Current Relative Quality Score Limitation

The current quality score is relative within each read.

Conceptually:

```text
score_i =
    max_score *
    (1 - penalty_i / worst_penalty_in_this_read)
```

This means:

```text
quality 50 in read A
```

does not necessarily represent the same absolute error probability as:

```text
quality 50 in read B
```

A poor read can still assign a high score to its least-poor bases.

Therefore the score should remain explicitly labeled:

```text
relative_quality
```

until it is empirically calibrated.

It should not silently evolve into:

```text
Phred quality
```

or:

```text
error probability
```

without validation.

---

# 15. Near-term Confidence Model Without ML

Before ML calibration exists, Signal can derive an interpretable evidence tier.

Example:

```rust
pub enum CallConfidenceClass {
    High,
    Medium,
    Review,
    NoCall,
}
```

Possible rule structure:

```text
HIGH:
    strong primary SNR
    no strong co-localized secondary
    normal spacing
    no saturation
    stable local baseline

MEDIUM:
    moderate SNR
    mild secondary evidence
    otherwise normal geometry

REVIEW:
    strong secondary
    compressed spacing
    baseline disturbance
    noisy region
    conflicting vendor evidence

NO_CALL:
    unresolved dominant signal
    severe low SNR
    multi-channel ambiguity
```

The rules must be treated as interim heuristic evidence, not calibrated error probabilities.

---

# 16. Future Calibrated Quality

The preferred long-term metric is:

```text
P(primary_call_is_wrong | signal evidence)
```

Possible output:

```json
{
  "primary": "A",
  "confidence": {
    "method": "signal.call-confidence/v1",
    "probability_correct": 0.9981,
    "calibrated": true
  }
}
```

Calibration should be validated using independently established truth.

Useful metrics include:

```text
Brier score
log loss
expected calibration error
reliability curves
error detection at fixed retained yield
```

---

# 17. P0: Introduce Sample-Level mtDNA Analysis

This is the most important architectural expansion.

The current core should remain capable of:

```text
one AB1 -> one read-level result
```

A new layer should aggregate multiple read-level results into:

```text
one biological sample -> one mtDNA analysis
```

---

# 18. Recommended Architecture

```text
                  sample manifest
                        |
                        v
             +----------------------+
             | trace classification |
             +----------------------+
                        |
       +----------------+----------------+
       |                |                |
       v                v                v
    AB1 #1           AB1 #2           AB1 #N
       |                |                |
       v                v                v
 read pipeline      read pipeline     read pipeline
       |                |                |
       +----------------+----------------+
                        |
                        v
             read/reference mappings
                        |
                        v
               sample consensus
                        |
          +-------------+-------------+
          |             |             |
          v             v             v
       variants     mixed sites    coverage/QC
          |             |             |
          +-------------+-------------+
                        |
                        v
                 haplogroup QC
                        |
                        v
                sample-level JSON
```

---

# 19. Sample Manifest

Do not infer biological sample structure solely from filenames.

Use an explicit manifest.

Example YAML:

```yaml
schema_version: 1

sample:
  id: SAMPLE_001

reference:
  name: rCRS

reads:
  - trace: SAMPLE_001_HV1_F.ab1
    amplicon: HV1
    direction: forward
    primer: L15997
    expected_region:
      start: 15950
      end: 16450

  - trace: SAMPLE_001_HV1_R.ab1
    amplicon: HV1
    direction: reverse
    primer: H16401
    expected_region:
      start: 15950
      end: 16450

  - trace: SAMPLE_001_HV2_F.ab1
    amplicon: HV2
    direction: forward
    expected_region:
      start: 1
      end: 450
```

JSON should also be supported if desired, but one canonical serialized manifest format is preferable for deterministic provenance.

---

# 20. Manifest Validation

Reject:

```text
duplicate trace path
duplicate logical read identity
invalid direction
invalid region
region outside reference
unknown reference
contradictory sample IDs
missing mandatory fields
ambiguous amplicon ownership
```

Optional warnings:

```text
same-direction reads only
missing reverse confirmation
unexpected number of reads
read mapped far outside expected region
```

---

# 21. New Core Domain Object: ReadObservation

Read-level analysis should eventually produce a stable internal representation suitable for consensus.

Example:

```rust
pub struct ReadObservation {
    pub read_id: String,

    pub trace_sha256: String,

    pub orientation: Orientation,

    pub amplicon: Option<String>,

    pub expected_region: Option<ReferenceRegion>,

    pub mapped_region: ReferenceSpan,

    pub positions: Vec<PositionObservation>,

    pub read_qc: ReadQualitySummary,
}
```

---

# 22. PositionObservation

Example:

```rust
pub struct PositionObservation {
    pub reference_position_1based: usize,

    pub call_index_0based: usize,

    pub primary: char,

    pub ambiguity: char,

    pub evidence: CallEvidence,

    pub alignment_state: AlignmentState,
}
```

For insertions, a coordinate representation should preserve:

```text
reference anchor
inserted sequence
source call indexes
```

For deletions:

```text
deleted reference span
left flank call
right flank call
```

---

# 23. Sample-Level Consensus

The consensus must not simply concatenate the strongest calls.

It should aggregate evidence.

Example position:

```text
Reference position 73

Read F1:
    A
    high confidence

Read F2:
    A
    medium confidence

Read R1:
    A
    high confidence

Read R2:
    G
    weak secondary / poor signal
```

A useful consensus result is not merely:

```text
A
```

It should retain:

```json
{
  "position": 73,

  "consensus": "A",

  "observations": {
    "total": 4,
    "forward": 2,
    "reverse": 2
  },

  "support": {
    "A": 3,
    "G": 1
  },

  "confidence": "high",

  "discordance": true
}
```

The production schema can remain compact while internal structures retain full evidence.

---

# 24. Consensus States

Suggested states:

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

The biological consensus base can remain separate:

```rust
pub enum ConsensusBase {
    Canonical(Nucleotide),
    Ambiguous(char),
    NoCall,
}
```

---

# 25. Bidirectional Confirmation Must Be First-Class

Variant evidence should record the strongest level of independent confirmation.

Suggested:

```rust
pub enum SupportLevel {
    SingleRead,
    SameDirectionReplicate,
    Bidirectional,
    IndependentAmplicon,
}
```

Example JSON:

```json
{
  "support": {
    "level": "bidirectional",
    "forward_reads": 1,
    "reverse_reads": 1,
    "independent_amplicons": 1
  }
}
```

This should directly influence:

```text
variant confidence
manual-review prioritization
mixed-base confidence
sample QC
```

---

# 26. Consensus Conflict Policy

Do not use a simplistic majority vote.

Possible evidence-aware policy:

```text
Case 1:
    A high
    A high
    G low

=> A, confirmed with minor discordance

Case 2:
    A high
    G high

=> discordant / manual review

Case 3:
    A high forward
    A high reverse

=> bidirectionally confirmed A

Case 4:
    A/G mixed signal forward
    A/G mixed signal reverse

=> strong mixed-base candidate

Case 5:
    A/G mixed signal only one weak read

=> weak mixed-base candidate / review
```

---

# 27. Separate Read-Level and Sample-Level Variants

Read-level variant:

```text
This electropherogram differs from rCRS here.
```

Sample-level variant:

```text
The combined evidence for this biological sample supports this difference.
```

These should be different domain types.

For example:

```rust
pub struct ReadVariant {
    ...
}

pub struct SampleVariant {
    pub canonical_variant: CanonicalVariant,

    pub observations: Vec<VariantObservation>,

    pub support_level: SupportLevel,

    pub confidence: SampleVariantConfidence,
}
```

---

# 28. P1: mtDNA-Specific Profiles

Current defaults focus on HVR regions.

This should be made explicit.

Example configuration:

```toml
[mtdna]
profile = "control-region"
reference = "rCRS"
```

Supported profiles could include:

```text
control-region
whole-mitogenome
custom
```

---

# 29. Control Region Profile

Example:

```toml
[mtdna.control_region]

regions = [
    [16024, 16365],
    [73, 340],
    [438, 576],
]
```

The exact defaults should remain versioned and documented.

---

# 30. Whole mtGenome Profile

Example:

```toml
[mtdna]
profile = "whole-mitogenome"
```

Conceptually:

```text
positions 1..16569
```

However, enabling the coordinate range alone does not provide whole-mtGenome support.

Whole-mtGenome Sanger processing also requires:

```text
multi-amplicon manifest
coverage assembly
overlap resolution
cross-amplicon consensus
gap reporting
sample-level publication
```

---

# 31. Expected Amplicon Regions

If primer or amplicon metadata is available, alignment should use it.

Current generic approach:

```text
read
 |
 v
search full circular mtDNA
```

Preferred:

```text
known amplicon
 |
 v
expected interval + margin
 |
 v
localized alignment
 |
 v
fallback to full reference if necessary
```

Example:

```text
expected region:
16000..16450

alignment search:
15900..16550 with circular handling
```

Benefits:

* lower computational cost;
* lower accidental placement risk;
* easier QC;
* clearer unexpected-mapping warnings.

---

# 32. Alignment Strategy

Keep current deterministic Gotoh logic as a reliable fallback.

Introduce optional constrained alignment:

```text
expected interval
        |
        v
extract circular reference window
        |
        v
affine-gap semi-global alignment
```

Later optimization:

```text
banded affine-gap alignment
```

Possible configuration:

```toml
[alignment]

expected_region_margin = 100

band_width = 64

fallback_to_full_reference = true
```

Do not introduce indexing complexity until real workloads require it.

---

# 33. Mapping QC

A read should generate warnings if:

```text
mapped outside expected region

unexpected orientation

unexpectedly short overlap

abnormally low identity

multiple near-equivalent placements

origin wrap inconsistent with expected amplicon

expected primer region absent
```

Example:

```json
{
  "mapping_qc": {
    "expected_region_match": false,
    "unexpected_orientation": false,
    "warnings": [
      "mapped_outside_expected_amplicon"
    ]
  }
}
```

---

# 34. P1: Better Deletion Evidence

Current deletion handling cannot inspect a deleted query base because no query base exists.

However, deletion confidence can still be estimated from surrounding evidence.

Use:

```text
left flank quality
right flank quality
local alignment stability
gap ambiguity
homopolymer context
forward/reverse confirmation
independent amplicon confirmation
local spacing behavior
```

Suggested:

```rust
pub struct DeletionEvidence {
    pub left_flank: Option<CallEvidenceSummary>,

    pub right_flank: Option<CallEvidenceSummary>,

    pub alignment_stability: AlignmentStability,

    pub homopolymer_context: bool,

    pub support_level: SupportLevel,
}
```

---

# 35. Alignment Stability

A variant is less trustworthy when multiple similarly scoring alignments imply different gap placement.

Consider computing:

```text
best alignment score
second-best relevant local representation score
score delta
```

or a simpler deterministic ambiguity indicator:

```text
multiple equivalent normalized placements
```

For repeat regions:

```text
AAA
AAAA
AAAAA
```

this evidence becomes particularly important.

---

# 36. P1: mtDNA Indel Representation

Maintain a canonical internal representation.

Example:

```rust
pub struct CanonicalVariant {
    pub position_1based: usize,
    pub reference: String,
    pub alternate: String,
}
```

Then create a separate mtDNA nomenclature projection.

Do not encode mtDNA-specific naming rules directly into low-level alignment or generic normalization logic.

Preferred layering:

```text
alignment event
     |
     v
canonical normalization
     |
     v
canonical variant
     |
     +----------------+
     |                |
     v                v
generic JSON     mtDNA nomenclature
```

---

# 37. Nomenclature Data Model

Example:

```rust
pub struct MtDnaVariantRepresentation {
    pub reference_name: String,

    pub reference_version: String,

    pub canonical: CanonicalVariant,

    pub mtdna_notation: String,

    pub nomenclature_method: String,

    pub nomenclature_version: String,
}
```

Example JSON:

```json
{
  "variant": {
    "canonical": {
      "position": 16189,
      "reference": "T",
      "alternate": "C"
    },

    "mtdna": {
      "reference": "rCRS",
      "notation": "16189C",
      "method": "signal.mtdna-nomenclature/v1"
    }
  }
}
```

---

# 38. Poly-C and Homopolymer Context

Homopolymer and poly-C contexts should be annotated explicitly.

Example:

```rust
pub struct SequenceContext {
    pub homopolymer_base: Option<Nucleotide>,

    pub homopolymer_length: usize,

    pub repeat_context: bool,

    pub control_region_poly_c: bool,
}
```

Variant/mixed-signal behavior in these regions should be handled conservatively.

---

# 39. Length Heteroplasmy Requires Separate Semantics

Length heteroplasmy is not equivalent to a standard isolated deletion.

A chromatogram after a length mixture may exhibit:

```text
clean signal before indel
        |
        v
mixture position
        |
        v
persistent phase-shifted double signal
```

This is biologically and signal-wise different from:

```text
single clean sequence containing a deletion
```

The pipeline should therefore eventually distinguish:

```rust
pub enum MtDnaEventClass {
    PointDifference,
    SimpleInsertion,
    SimpleDeletion,
    MixedPointCandidate,
    LengthMixtureCandidate,
}
```

Do not infer length heteroplasmy purely from one normalized alignment gap.

---

# 40. Possible Length-Mixture Evidence

Potential features:

```text
clean pre-event signal

abrupt onset of mixed peaks

persistent post-event double peaks

spacing phase shift

candidate indel length

agreement with known homopolymer context

forward/reverse recurrence

replicate recurrence
```

Possible internal representation:

```rust
pub struct LengthMixtureCandidate {
    pub anchor_position_1based: usize,

    pub candidate_length_delta: i32,

    pub onset_call_index: usize,

    pub evidence_span_calls: Range<usize>,

    pub confidence: EvidenceClass,
}
```

This should initially remain a review candidate rather than a quantified heteroplasmy result.

---

# 41. P1: Mixed-Base Candidate Detection

The first mixed-signal implementation should deliberately avoid the word `heteroplasmy`.

Output terminology:

```text
mixed_base_candidate
```

Possible representation:

```rust
pub struct MixedBaseCandidate {
    pub position_1based: usize,

    pub major: Nucleotide,

    pub minor: Nucleotide,

    pub major_signal: AlleleSignalEvidence,

    pub minor_signal: AlleleSignalEvidence,

    pub observed_ratio: f64,

    pub support_level: SupportLevel,

    pub confidence: EvidenceClass,
}
```

---

# 42. Mixed-Base Evidence

Useful fields:

```text
major corrected amplitude
minor corrected amplitude

major SNR
minor SNR

minor/major amplitude ratio

peak offset

peak-width similarity

peak-shape similarity

local spacing

neighboring base interference

signal saturation

baseline stability

forward support

reverse support

replicate support
```

---

# 43. Example Mixed-Base Output

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

This is useful evidence without claiming:

```text
24% heteroplasmy
```

---

# 44. P2: Heteroplasmy Calibration

Only after controlled validation should Signal estimate allele fractions.

Use artificial or verified mixtures such as:

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

The exact experiment design should depend on target assay performance.

---

# 45. Calibration Model

Raw observed peak ratio is not automatically equal to biological mixture fraction.

Instead:

```text
observed signal features
        |
        v
calibration model
        |
        v
estimated minor fraction
        |
        v
uncertainty interval
```

Possible model inputs:

```text
major/minor corrected ratio
major/minor SNR
base substitution pair
sequence context
strand
instrument/run metadata if appropriate
local peak width
local baseline
```

---

# 46. Assay-Specific Limits

Before emitting a heteroplasmy result, establish:

```text
LoB = Limit of Blank

LoD = Limit of Detection

LoQ = Limit of Quantification
```

Example configuration/provenance:

```json
{
  "heteroplasmy_method": {
    "name": "signal.sanger-mixture/v1",

    "validated_lod": 0.12,

    "validated_loq": 0.18,

    "model_sha256": "..."
  }
}
```

---

# 47. Heteroplasmy Output States

Possible semantics:

```rust
pub enum HeteroplasmyStatus {
    NotEvaluated,

    MixedSignalBelowValidatedLod,

    DetectedNotQuantifiable,

    Quantifiable,
}
```

Example:

```json
{
  "status": "detected_not_quantifiable",

  "estimated_minor_fraction": null,

  "observed_signal_ratio": 0.11,

  "validated_lod": 0.10,

  "validated_loq": 0.18
}
```

This is scientifically more honest than reporting a precise percentage unsupported by assay validation.

---

# 48. Confirmation Requirements

Heteroplasmy policy may require:

```text
bidirectional confirmation
```

or:

```text
independent replicate confirmation
```

depending on validated assay rules.

Example configuration:

```toml
[mtdna.heteroplasmy]

minimum_support = "bidirectional"
```

The software should support policy configuration only after the assay validation establishes the requirement.

---

# 49. P1/P2: Haplogroup Assignment

Haplogroup assignment should be added primarily as:

```text
sample QC
```

rather than as a mechanism to force variant calls.

Recommended uses:

```text
detect missing expected phylogenetic mutations

detect unexpected private mutation burden

detect sample mix-up

detect possible contamination

detect improbable mutation combinations

flag low-information partial profiles
```

---

# 50. Version the Haplogroup Tree

Do not hardcode an unversioned phylogenetic tree.

Example:

```rust
pub struct HaplogroupResource {
    pub name: String,
    pub version: String,
    pub sha256: String,
}
```

Example output:

```json
{
  "haplogroup": {
    "resource": {
      "name": "mitoLEAF",
      "version": "2026-xx",
      "sha256": "..."
    },

    "best_assignment": "B5a",

    "confidence": "partial",

    "alternatives": [
      "B5",
      "B5a"
    ]
  }
}
```

---

# 51. Partial-Region Haplogroup Policy

Do not force a terminal leaf assignment when only HVR information is available.

Example:

```text
observed data supports:

B5
 |
 +-- B5a
 |
 +-- B5b

but does not distinguish B5a vs B5b
```

Output:

```json
{
  "best_assignment": "B5",

  "resolution": "ancestral",

  "unresolved_descendants": [
    "B5a",
    "B5b"
  ]
}
```

---

# 52. Haplogroup QC Model

Example:

```rust
pub struct HaplogroupQc {
    pub expected_mutations_present: Vec<MtVariant>,

    pub expected_mutations_missing: Vec<MtVariant>,

    pub unexpected_mutations: Vec<MtVariant>,

    pub conflicting_markers: Vec<MtVariant>,

    pub status: HaplogroupQcStatus,
}
```

Status:

```rust
pub enum HaplogroupQcStatus {
    Consistent,
    LimitedInformation,
    ReviewRecommended,
    StrongConflict,
}
```

---

# 53. Never Use Haplogroup to Overrule Strong Signal

Incorrect:

```text
tree expects A
signal strongly says G
therefore force A
```

Correct:

```text
signal strongly says G

haplogroup model says this is unexpected

=> report G
=> add phylogenetic QC warning
```

Observed evidence must remain primary.

---

# 54. P2: NUMT and Contamination Awareness

Software cannot solve NUMT amplification by itself.

Primer design and laboratory methods remain critical.

Signal can nevertheless provide useful evidence.

Potential inputs:

```text
primer identity
expected amplicon
expected orientation
known off-target regions
nuclear reference resources
```

---

# 55. NUMT-Oriented QC

Possible checks:

```text
unexpected mapping

unexpectedly high mismatch pattern

persistent mixed signal across many sites

haplogroup inconsistency

multiple coherent alternative alleles

amplicon mapping ambiguity

known NUMT-like sequence similarity
```

These should generate warnings such as:

```text
possible_off_target_amplification

possible_mixed_template

possible_numt_interference
```

not definitive claims.

---

# 56. Primer Metadata

Recommended manifest extension:

```yaml
reads:
  - trace: SAMPLE_001_HV1_F.ab1

    primer:
      name: L15997

      sequence: CACCATTAGCACCCAAAGCT

    expected_region:
      start: 15950
      end: 16450
```

Primer sequence should be optional because older datasets may not retain it.

---

# 57. Primer QC

Possible checks:

```text
primer sequence detectable at expected location

primer maps uniquely enough to mtDNA

observed read starts near expected primer site

orientation matches primer expectation
```

Do not reject a valid trace merely because primer sequence has been trimmed or is not detectable.

---

# 58. P0/P1: Sample-Level Coverage

A sample result should describe exactly which mtDNA regions were observed.

Example:

```json
{
  "coverage": {
    "reference_length": 16569,

    "covered_positions": 812,

    "callable_positions": 790,

    "high_confidence_positions": 741,

    "regions": [
      {
        "start": 16024,
        "end": 16365,
        "coverage_fraction": 0.997
      }
    ]
  }
}
```

---

# 59. Coverage States

Per reference position:

```rust
pub enum CoverageState {
    Uncovered,

    CoveredNoCall,

    SingleRead,

    SingleDirection,

    Bidirectional,
}
```

This distinction matters for interpreting absence of a variant.

---

# 60. P0: Introduce a Sample-Level Result Contract

Keep existing contracts unchanged.

Do not mutate:

```text
signal.basecalls/v1

signal.analysis/v5
```

Add a new contract.

Suggested:

```text
signal.mtdna-sample/v1
```

---

# 61. Example Top-Level Sample JSON

```json
{
  "schema": "signal.mtdna-sample/v1",

  "provenance": {
    "signal_version": "0.x.x",

    "manifest_sha256": "...",

    "configuration_sha256": "...",

    "reference": {
      "name": "rCRS",
      "sha256": "..."
    }
  },

  "sample": {
    "read_count": 4,

    "successful_reads": 4
  },

  "coverage": {
    "callable_positions": 780
  },

  "consensus": {
    "callable_bases": 780,

    "no_calls": 4,

    "discordant_positions": 2
  },

  "variants": [],

  "mixed_base_candidates": [],

  "haplogroup": null,

  "warnings": []
}
```

The compact production JSON should avoid embedding complete read-level signal arrays.

---

# 62. Sample-Level Provenance

Record all trace identities.

Example:

```json
{
  "inputs": [
    {
      "logical_read": "HV1_F",
      "sha256": "..."
    },

    {
      "logical_read": "HV1_R",
      "sha256": "..."
    }
  ]
}
```

Avoid including identifying filenames in the compact result unless required by the product contract.

---

# 63. Read-Level Result Reuse

Do not duplicate scientific algorithms in the sample pipeline.

Preferred:

```text
AB1
 |
 v
existing read pipeline
 |
 v
typed read result
 |
 v
sample assembler
```

Do not:

```text
sample pipeline
 |
 +--> separately decode AB1 again
 |
 +--> separately call bases again
```

There should remain one authoritative implementation for each scientific stage.

---

# 64. Suggested New Source Layout

```text
src/
├── alignment/
├── basecalling/
├── checksum.rs
├── cli/
├── config/
├── error/
├── logger.rs
├── model/
├── pipeline/
├── quality_control/
├── reference/
├── report/
├── signal_processing/
├── trace/
├── variant_calling/
│
├── peak_detection/
│   ├── mod.rs
│   ├── baseline.rs
│   ├── candidates.rs
│   ├── evidence.rs
│   ├── locus.rs
│   └── metrics.rs
│
└── mtdna/
    ├── mod.rs
    ├── manifest.rs
    ├── read.rs
    ├── consensus.rs
    ├── coverage.rs
    ├── variants.rs
    ├── mixed.rs
    ├── length_mixture.rs
    ├── nomenclature.rs
    ├── haplogroup.rs
    ├── numt.rs
    └── qc.rs
```

Report additions:

```text
src/report/
├── ...
└── mtdna_sample.rs
```

---

# 65. Dependency Direction

Recommended dependency direction:

```text
trace
  |
  v
peak_detection
  |
  v
basecalling
  |
  v
signal_processing
  |
  v
quality_control
  |
  v
alignment
  |
  v
variant_calling
```

mtDNA layer:

```text
read scientific results
        |
        v
      mtdna
        |
        v
      report
```

Forbidden:

```text
basecalling -> mtdna

alignment -> report

quality_control -> CLI
```

Low-level scientific modules must remain unaware of mtDNA orchestration.

---

# 66. CLI Evolution

Keep:

```bash
signal basecall sample.ab1
```

and:

```bash
signal analyze sample.ab1 \
  --reference references/rCRS.fasta
```

Add something conceptually like:

```bash
signal mtdna sample sample.yaml
```

or:

```bash
signal mtdna analyze sample.yaml
```

A simple preferred form:

```bash
signal mtdna sample sample.yaml
```

---

# 67. Potential Future CLI

```text
signal
├── basecall
├── analyze
└── mtdna
    ├── sample
    ├── validate-manifest
    └── inspect
```

Avoid too many commands initially.

Recommended MVP:

```text
signal mtdna sample
```

only.

---

# 68. Output Naming

Suggested:

```text
results/
└── <sample-id>/
    └── sample.mtdna.json
```

However, if sample IDs are sensitive, an opaque run-local identity may be preferable.

Alternative:

```text
results/
└── <manifest-hash-prefix>/
    └── sample.mtdna.json
```

The privacy policy should explicitly define this.

---

# 69. P1: Immutable Batch Runs

The current clean-rerun wrapper removes selected outputs before rerunning.

A safer research workflow is immutable run directories.

Suggested:

```text
runs/
└── 2026-09-07T101500Z/
    ├── run.json
    ├── manifest.sha256
    ├── config.sha256
    ├── samples/
    │   ├── SAMPLE_001/
    │   └── SAMPLE_002/
    └── logs/
```

---

# 70. Run Manifest

Example:

```json
{
  "run_id": "2026-09-07T101500Z",

  "signal_version": "0.x.x",

  "configuration_sha256": "...",

  "reference_sha256": "...",

  "samples": [
    {
      "id": "opaque-sample-1",
      "status": "complete"
    },

    {
      "id": "opaque-sample-2",
      "status": "failed"
    }
  ]
}
```

---

# 71. Resume Support

Possible workflow:

```bash
signal-batch run manifest.yaml

signal-batch resume RUN_ID
```

or preserve orchestration outside the Rust binary.

The core requirement should be:

```text
completed sample outputs are immutable
```

and:

```text
resume never silently changes an existing successful result
```

---

# 72. Sample Atomicity

Current trace result publication is atomic.

Sample-level analysis should add sample atomicity.

Desired:

```text
all required reads complete
        |
        v
sample consensus complete
        |
        v
sample JSON serialized
        |
        v
atomic publish
```

Failure should leave no partially published sample result.

Intermediate read artifacts may still exist in the run workspace.

---

# 73. P0: Real Validation Corpus

Synthetic unit tests are necessary but insufficient.

A scientifically meaningful validation corpus should contain approved real AB1 traces.

Stratify by:

```text
instrument

run

signal quality

HVI

HVII

HVIII

coding region

forward reads

reverse reads

homopolymers

poly-C tracts

known indels

mixed signals

read ends

low-input samples
```

---

# 74. Truth Hierarchy

Preferred truth sources:

```text
1. independent high-depth sequencing

2. independently established consensus

3. bidirectional high-quality Sanger consensus

4. validated reference material

5. expert-curated review
```

Avoid using current Signal output as its own training or validation truth.

---

# 75. Controlled Synthetic Signal Tests

Keep synthetic tests for algorithm behavior.

Construct tests for:

```text
single clean peak

two co-localized peaks

two non-co-localized peaks

three-channel interference

saturated primary peak

baseline drift

noise spikes

compressed spacing

expanded spacing

homopolymer

read-end degradation

insertion-like spacing

deletion-like spacing
```

---

# 76. Mixed-Signal Controlled Experiments

For future heteroplasmy calibration:

```text
major/minor combinations:

A/G
A/C
A/T
C/G
C/T
G/T
```

Mixture fractions:

```text
0
0.025
0.05
0.10
0.15
0.20
0.30
0.40
0.50
```

Potentially both orientations.

Different sequence contexts should be represented.

---

# 77. Evaluation Metrics

## Basecalling

Measure:

```text
base accuracy

substitution error

insertion error

deletion error

no-call rate

ambiguity rate
```

---

## Quality calibration

Measure:

```text
Brier score

log loss

calibration error

reliability curve

false high-confidence error rate
```

---

## Variant calling

Measure:

```text
SNV sensitivity

SNV precision

indel sensitivity

indel precision

false positive rate

false negative rate
```

---

## Mixed-base candidate detection

Measure:

```text
sensitivity by mixture fraction

specificity

false mixed-base rate

precision

performance by nucleotide pair

performance by strand

performance by sequence context
```

---

## Consensus

Measure:

```text
consensus accuracy

discordance rate

bidirectional agreement

read-to-consensus conflict rate

coverage completeness
```

---

## Length mixture

Measure separately:

```text
event detection sensitivity

event false-positive rate

candidate length accuracy

anchor accuracy

forward/reverse reproducibility
```

---

# 78. Dataset Splitting

If ML is introduced, do not randomly split individual calls from the same biological samples across train/test.

Split by:

```text
sample

run

instrument

ideally acquisition batch
```

Example:

```text
TRAIN:
    runs A-D

VALIDATION:
    run E

TEST:
    completely held-out runs F-G
```

Otherwise local signal characteristics can leak into evaluation.

---

# 79. P2/P3: ML Roadmap

ML should not replace deterministic components such as:

```text
ABIF parsing

coordinate conversion

reference wrapping

indel normalization

checksum validation

schema validation

atomic publication
```

ML is appropriate for uncertain observational tasks.

Recommended order:

```text
1. per-call confidence calibration

2. trace quality / resequence recommendation

3. artifact classification

4. out-of-distribution detection

5. trimming recommendation

6. base-call correction

7. variant review prioritization

8. mixed-template estimation

9. end-to-end basecalling
```

---

# 80. ML Feature Boundary

Retain the current roadmap principle:

```text
scientific pipeline
      |
      v
completed typed evidence
      |
      v
feature extraction
      |
      v
versioned FeatureSet
      |
      v
training/inference
```

Do not place feature engineering inside:

```text
report serialization
```

or:

```text
CLI code
```

---

# 81. ML Features Worth Retaining

Per-call:

```text
PLOC

refined locus

window width

A peak height

C peak height

G peak height

T peak height

corrected heights

channel SNRs

peak offsets

peak widths

prominence

major/minor ratio

local spacing

baseline statistics

noise statistics

retained status

current heuristic quality

rolling noisy-region membership
```

---

# 82. Reference-Aware Features

For tasks where the reference is allowed:

```text
reference base

alignment context

distance to gap

homopolymer length

repeat context

read orientation

expected amplicon

mapping identity
```

Do not use these for a model intended to perform reference-free basecalling.

---

# 83. Prevent Target Leakage

Examples:

Do not predict:

```text
variant accepted by filter
```

using:

```text
filter exclusion reason
```

Do not predict:

```text
quality pass/fail
```

using:

```text
current threshold decision
```

Do not predict:

```text
base correctness
```

using:

```text
truth-derived alignment field
```

unless that same field is available at real inference time.

---

# 84. Model Provenance

Any inference result should include:

```text
model name

model semantic version

model checksum

feature set name

feature set version

feature definition checksum

calibration identity
```

Example:

```json
{
  "confidence_model": {
    "name": "signal-call-confidence",
    "version": "1.0.0",
    "sha256": "...",

    "feature_set": {
      "name": "signal.call-features",
      "version": "2",
      "sha256": "..."
    }
  }
}
```

---

# 85. P1: Signal Processing Improvements

Current rolling SNR should remain as an observational layer.

Potential future processed signal:

```text
decoded analyzed channels
        |
        +----------------------+
        |                      |
        v                      v
   untouched source       processed projection
                               |
                               v
                        baseline corrected
                               |
                               v
                       optional smoothing
```

Never overwrite decoded channels.

---

# 86. Baseline Correction

Candidate approaches should be benchmarked, not selected solely by visual appearance.

Requirements:

```text
preserve genuine secondary peaks

preserve peak positions

not distort peak ratios excessively

improve low-frequency baseline drift

deterministic output
```

Store method identity:

```json
{
  "baseline": {
    "method": "signal.baseline/v1",
    "parameters": {
      "...": "..."
    }
  }
}
```

---

# 87. Smoothing

If smoothing is added:

```text
raw analyzed channel
       |
       v
peak-preserving smoothing
       |
       v
processed projection
```

Validate specifically for:

```text
minor allele preservation

compressed peaks

homopolymers

read ends
```

A denoiser that improves visual smoothness while deleting true low-frequency secondary alleles is unacceptable for mtDNA mixture analysis.

---

# 88. Saturation Detection

Add a saturation feature.

Possible criteria:

```text
repeated maximum ADC values

flat peak tops

unusually broad clipped peaks
```

Example:

```rust
pub enum SaturationState {
    None,
    Possible,
    Strong,
}
```

Saturated peaks can invalidate peak-height ratio assumptions.

---

# 89. Artifact Classification

Possible artifacts:

```text
impulse spike

baseline jump

dye blob

broad peak

compressed peaks

pull-up/crosstalk

saturation

phase-shifted signal

read-end collapse
```

Start with deterministic feature flags.

Only later add ML classification if needed.

---

# 90. Variant Evidence Should Include Signal Context

Current noisy regions are observation-only.

Retain that scientific conservatism.

But variant evidence should record whether the event overlaps concerning signal.

Example:

```json
{
  "signal_context": {
    "candidate_noisy_region": true,

    "local_primary_snr": 2.1,

    "secondary_signal_present": false
  }
}
```

Do not necessarily hard-filter it.

This allows sample consensus to distinguish:

```text
weak one-read difference
```

from:

```text
two-direction high-quality difference
```

---

# 91. Review Status

Sample-level variants can use evidence classes:

```rust
pub enum VariantReviewStatus {
    Strong,
    Supported,
    ReviewRecommended,
    InsufficientEvidence,
}
```

Example rules:

```text
Strong:
    bidirectional high-confidence support

Supported:
    multiple compatible observations

ReviewRecommended:
    one strand only
    low SNR
    repeat context
    disagreement

InsufficientEvidence:
    no reproducible support
```

These statuses should not be mistaken for clinical interpretation.

---

# 92. P1: Sample QC Summary

Sample-level output should summarize:

```text
read completion

coverage

single-direction positions

discordant positions

no-call positions

reported variants

mixed-base candidates

length-mixture candidates

haplogroup QC

mapping warnings

possible contamination/off-target warnings
```

Example:

```json
{
  "qc": {
    "status": "review",

    "read_count": 4,

    "failed_reads": 0,

    "single_direction_positions": 12,

    "discordant_positions": 2,

    "mixed_base_candidates": 1,

    "warnings": [
      "one_variant_single_direction_only"
    ]
  }
}
```

---

# 93. QC Status Must Be Explainable

Avoid opaque:

```text
QC = 72
```

Prefer:

```text
status = review
reasons = [...]
```

Example:

```json
{
  "status": "review",

  "reasons": [
    "position_16189_requires_manual_review",
    "hv2_reverse_read_missing"
  ]
}
```

---

# 94. Privacy

mtDNA data is potentially identifying.

Continue treating:

```text
AB1 files

basecall sequences

variant profiles

haplogroup assignments

input hashes

sample manifests

derived JSON
```

as sensitive research data.

---

# 95. Avoid Hidden Identifiers

A SHA-256 hash of a private AB1 file can still act as a stable identifier.

Do not assume:

```text
hash == anonymous
```

Document this explicitly.

---

# 96. Compact vs Evidence Output

Consider maintaining two conceptual output classes.

Production result:

```text
signal.mtdna-sample/v1
```

Compact and privacy-aware.

Research/evidence export:

```text
signal.mtdna-evidence/v1
```

Optional and more detailed.

Do not overload the compact production schema with complete signal vectors.

---

# 97. Backwards Compatibility

Do not silently change semantics of:

```text
signal.basecalls/v1

signal.analysis/v5
```

Behavior-changing improvements can introduce:

```text
new method versions
```

without necessarily changing the outer schema if output semantics permit it.

But structural or semantic breaking changes should trigger:

```text
new output schema major version
```

---

# 98. Suggested Method Versioning

Examples:

```text
signal.peak_recall/v3

signal.locus_evidence/v1

signal.call-confidence/v1

signal.sample-consensus/v1

signal.mtdna-variant/v1

signal.mtdna-mixed-base/v1

signal.mtdna-nomenclature/v1

signal.haplogroup-qc/v1
```

Avoid generic:

```text
algorithm = "new"
```

---

# 99. Configuration Evolution

Recommended new sections:

```toml
schema_version = 5

[mtdna]
profile = "control-region"

[mtdna.consensus]
minimum_support = 1
prefer_bidirectional = true

[mtdna.mixed_signal]
enabled = true

[mtdna.haplogroup]
enabled = false

[peak_detection]
locus_refinement = true
maximum_refinement_samples = 3

[quality]
method = "evidence-v1"
```

Exact values must be determined through validation rather than guessed.

---

# 100. Do Not Expose Unvalidated Defaults as Scientific Truth

Avoid documentation such as:

```text
secondary ratio 0.20 means heteroplasmy
```

unless validation demonstrates that rule.

Prefer:

```text
This threshold identifies candidate secondary signal and does not establish heteroplasmy.
```

---

# 101. Proposed P0 Deliverables

P0 should make Signal scientifically stronger without making large biological claims.

Deliver:

```text
1. peak co-localization

2. explicit per-locus evidence

3. baseline-corrected amplitudes

4. local channel SNR

5. peak offset/prominence

6. sample manifest

7. multi-read sample consensus

8. bidirectional support

9. sample coverage

10. real-trace validation harness
```

---

# 102. Proposed P1 Deliverables

```text
1. PLOC refinement

2. constrained amplicon alignment

3. deletion flank evidence

4. mtDNA-specific variant projection

5. homopolymer/poly-C context

6. mixed-base candidate detection

7. haplogroup QC

8. immutable batch run model

9. sample-level output schema
```

---

# 103. Proposed P2 Deliverables

```text
1. controlled mixture experiments

2. calibrated call confidence

3. heteroplasmy LoB/LoD/LoQ

4. quantitative mixture estimation

5. length-mixture detection

6. NUMT/off-target QC

7. whole-mtGenome sample assembly

8. artifact classification
```

---

# 104. Proposed P3 Deliverables

```text
1. ML call-confidence models

2. ML trace triage

3. ML trimming recommendation

4. ML base correction

5. ML mixed-template decomposition

6. optional advanced waveform models
```

---

# 105. Recommended PR Sequence

A practical implementation should use smaller reviewable PRs.

---

## PR 1 — Peak Evidence Foundations

Add:

```text
peak_detection module

baseline-corrected amplitude

peak prominence

peak offsets

per-channel local SNR

co-localization helpers
```

Do not change variant semantics yet.

Tests:

```text
synthetic clean peaks

offset peaks

non-colocalized secondary peaks

baseline drift

ties
```

---

## PR 2 — Basecalling v3

Change call logic to consume locus/peak evidence.

Major changes:

```text
secondary channel must be co-localized

signal metrics become explicit

existing primary/IUPAC behavior remains conservative
```

Introduce:

```text
signal.peak_recall/v3
```

Compare outputs against current v2 on regression fixtures.

---

## PR 3 — Read Evidence Contract Internals

Create internal typed representation:

```text
ReadObservation

PositionObservation

CallEvidence
```

Do not change external JSON yet.

This creates a stable boundary for sample assembly.

---

## PR 4 — mtDNA Manifest

Implement:

```text
manifest parser

strict validation

trace identity mapping

direction

amplicon

expected region

primer metadata
```

No consensus yet.

---

## PR 5 — Sample Consensus MVP

Implement:

```text
multiple read inputs

read pipeline reuse

reference coordinate aggregation

coverage

simple conservative consensus

bidirectional support
```

Add:

```text
signal.mtdna-sample/v1
```

---

## PR 6 — Sample Variant Aggregation

Create:

```text
SampleVariant

VariantObservation

SupportLevel

VariantReviewStatus
```

Aggregate equivalent canonical variants across reads.

---

## PR 7 — Constrained Alignment

Use:

```text
expected amplicon region

margin

fallback full-reference search
```

Add mapping QC.

Benchmark runtime.

---

## PR 8 — mtDNA Nomenclature and Sequence Context

Add:

```text
homopolymer context

poly-C context

mtDNA nomenclature projection

separate canonical and display representation
```

---

## PR 9 — Mixed-Base Candidates

Implement:

```text
co-localized major/minor signal evidence

cross-read aggregation

bidirectional confirmation

mixed_base_candidate
```

Do not quantify heteroplasmy.

---

## PR 10 — Haplogroup QC

Add versioned phylogenetic resource.

Implement:

```text
partial assignment

expected/missing markers

unexpected markers

conflict warnings
```

---

# 106. PRs After Validation Corpus Exists

Only after enough independent truth exists:

```text
PR 11:
calibrated call confidence

PR 12:
controlled heteroplasmy calibration

PR 13:
quantitative heteroplasmy reporting

PR 14:
length-mixture analysis

PR 15:
whole-mitogenome assembly
```

---

# 107. Testing Strategy

Every scientific change should include:

```text
unit tests

property/invariant tests

synthetic signal fixtures

real-trace regression tests

schema tests

cross-version regression tests
```

---

# 108. Important Invariants

Examples:

```text
decoded source signal never mutated

channel order always A/C/G/T

call indexes remain 0-based

reference positions remain 1-based externally

internal reference intervals remain 0-based half-open

reverse-orientation mappings preserve original call identity

canonical variants validate against reference

sample consensus never invents coverage

mixed candidate must retain source observations
```

---

# 109. Peak Invariants

```text
selected peak position belongs to its search interval

corrected amplitude cannot be negative after max(0, ...)

SNR must be finite

peak offsets must fit integer bounds

secondary allele evidence must reference a real channel peak

co-localization is deterministic
```

---

# 110. Sample Consensus Invariants

```text
every consensus-support observation maps to same reference position

no observation belongs to two samples

read orientation is explicit

reference identity matches across all reads

configuration compatibility is validated

sample publication occurs only after successful aggregation
```

---

# 111. Cross-Read Configuration Compatibility

A sample must not silently combine reads analyzed with incompatible scientific settings.

Verify:

```text
reference checksum

relevant configuration identity

algorithm versions

coordinate conventions

haplogroup resource identity if applicable
```

If preprocessing differs intentionally, make it explicit.

---

# 112. Reference Identity

Do not rely only on:

```text
reference name = rCRS
```

Also retain:

```text
reference SHA-256
reference length
reference topology
```

Example:

```json
{
  "reference": {
    "name": "rCRS",
    "length": 16569,
    "topology": "circular",
    "sha256": "..."
  }
}
```

---

# 113. Resource Versioning

External resources should be immutable by identity.

Examples:

```text
rCRS

haplogroup tree

NUMT resource

primer database

nomenclature rule set
```

Record a version and checksum.

---

# 114. Benchmarking

Track:

```text
time/read

memory/read

time/sample

peak detection time

alignment time

consensus time

haplogroup time
```

Especially compare:

```text
full circular alignment
vs
expected-region alignment
```

---

# 115. Alignment Performance

For one approximately 700-base read against duplicated mtDNA:

```text
query length ~700

working circular reference length ~33,138

DP cells ~23 million
```

This is manageable for isolated reads but expensive for large sample batches.

Expected-region alignment can reduce this by orders of magnitude.

---

# 116. Whole mtGenome Performance

For whole-mitogenome Sanger:

```text
many overlapping amplicons
many traces/sample
```

The problem is not primarily reference length.

The important concerns become:

```text
read orchestration

overlap consensus

coverage gaps

conflicts

batch throughput
```

Optimize those after correctness is established.

---

# 117. Observability

Keep operational logs free of unnecessary biological payloads.

Good log fields:

```text
run ID

stage

elapsed time

call count

mapped span

variant count

warning count

failure category
```

Avoid logging:

```text
full sequence

full genotype profile

all alleles

raw signal vectors
```

unless explicitly using a secure research debug mode.

---

# 118. Failure Classification

Useful sample-level errors:

```text
ManifestInvalid

ReferenceMismatch

ReadAnalysisFailed

ReadConfigurationMismatch

InsufficientCoverage

ConsensusFailed

MappingConflict

ResourceVersionMismatch

HaplogroupResourceInvalid
```

Warnings should remain separate from hard failures.

---

# 119. Warning Categories

Suggested:

```text
SingleDirectionCoverage

ReadDiscordance

UnexpectedMapping

WeakVariantEvidence

MixedSignalCandidate

LengthMixtureCandidate

HomopolymerVariant

HaplogroupConflict

PossibleOffTarget

LowCoverage

ReferenceOriginWrap
```

---

# 120. Manual Review

Future review tooling could display:

```text
reference position

forward chromatogram

reverse chromatogram

called alleles

major/minor signals

peak ratios

local SNR

alignment context

haplogroup expectation
```

The core pipeline should expose enough structured evidence to build such a viewer later.

Do not embed UI concerns into scientific modules.

---

# 121. Why ML Should Not Be the First Next Step

The current deterministic foundation lacks enough validated independent truth for ML to be the highest-value immediate improvement.

Without better evidence geometry and sample consensus, ML risks learning:

```text
vendor PLOC behavior

current heuristic thresholds

instrument-specific artifacts

sample duplication

run-specific scaling
```

instead of biological call correctness.

First improve:

```text
evidence representation

truth corpus

sample structure

validation
```

Then ML becomes much more useful.

---

# 122. Recommended Immediate Focus

If only three major efforts can be funded, choose:

## 1. Peak Evidence v2

```text
co-localization

baseline correction

prominence

local SNR

position refinement
```

## 2. Sample-Level Consensus

```text
manifest

multiple reads

forward/reverse aggregation

coverage

sample variants
```

## 3. Scientific Validation

```text
approved real AB1 corpus

independent truth

regression benchmark

controlled mixtures
```

These three unlock almost every later improvement.

---

# 123. Target Architecture

The long-term architecture should resemble:

```text
                                   +--------------------+
AB1 ------------------------------>| ABIF decode        |
                                   +--------------------+
                                              |
                                              v
                                   +--------------------+
                                   | peak detection     |
                                   | + locus evidence   |
                                   +--------------------+
                                              |
                                              v
                                   +--------------------+
                                   | basecalling        |
                                   +--------------------+
                                              |
                                              v
                                   +--------------------+
                                   | signal/QC          |
                                   +--------------------+
                                              |
                                              v
                                   +--------------------+
                                   | read alignment     |
                                   +--------------------+
                                              |
                                              v
                                   +--------------------+
                                   | ReadObservation    |
                                   +--------------------+
                                              |
                  +---------------------------+---------------------------+
                  |                           |                           |
                  v                           v                           v
            forward read               reverse read                other reads
                  |                           |                           |
                  +---------------------------+---------------------------+
                                              |
                                              v
                                   +--------------------+
                                   | sample consensus   |
                                   +--------------------+
                                              |
                      +-----------------------+-----------------------+
                      |                       |                       |
                      v                       v                       v
                sample variants        mixed candidates           coverage
                      |                       |                       |
                      +-----------------------+-----------------------+
                                              |
                                              v
                                   +--------------------+
                                   | mtDNA-specific QC  |
                                   | nomenclature       |
                                   | haplogroup         |
                                   | NUMT warnings      |
                                   +--------------------+
                                              |
                                              v
                                   signal.mtdna-sample/v1
```

---

# 124. Desired Scientific Progression

The project should progress through increasing levels of biological claim.

## Level 1

```text
signal observation
```

Examples:

```text
secondary peak detected
low SNR
compressed spacing
```

---

## Level 2

```text
read-level sequence difference
```

Example:

```text
this trace differs from rCRS at position X
```

---

## Level 3

```text
sample-level supported variant
```

Example:

```text
the sample has consistent bidirectional support for difference X
```

---

## Level 4

```text
mixed-template candidate
```

Example:

```text
consistent secondary A/G signal appears in both directions
```

---

## Level 5

```text
validated heteroplasmy detection
```

Requires assay validation.

---

## Level 6

```text
quantitative heteroplasmy
```

Requires quantitative calibration and LoQ.

This hierarchy should remain explicit in documentation and data models.

---

# 125. Definition of Success

Signal can reasonably be described as an mtDNA Sanger analysis pipeline when it can reliably perform:

```text
multi-read sample ingestion

forward/reverse consensus

mtDNA coordinate handling

circular reference handling

sample-level SNV/indel calls

repeat-aware indel representation

coverage reporting

mixed-signal candidate reporting

sample-level evidence tracking

versioned phylogenetic QC

real-trace validated performance
```

Quantitative heteroplasmy does not need to be part of the first successful mtDNA release.

---

# 126. Proposed Release Milestones

## Signal 0.2 — Better Evidence

Focus:

```text
peak co-localization

baseline-corrected signal

per-locus SNR

peak geometry

PLOC refinement
```

Goal:

> Improve read-level evidence quality without expanding biological claims.

---

## Signal 0.3 — mtDNA Sample

Focus:

```text
sample manifest

multi-read orchestration

coverage

forward/reverse consensus

sample-level variants
```

Goal:

> Move from electropherogram analysis to biological-sample analysis.

---

## Signal 0.4 — mtDNA Interpretation

Focus:

```text
mtDNA nomenclature

homopolymer handling

mixed-base candidates

haplogroup QC
```

Goal:

> Provide mtDNA-specific interpretation without unvalidated heteroplasmy quantification.

---

## Signal 0.5 — Calibrated Confidence

Focus:

```text
real truth corpus

calibrated per-call confidence

variant confidence

trace triage
```

Goal:

> Replace read-relative heuristics with empirically interpretable confidence.

---

## Signal 0.6 — Heteroplasmy Research

Focus:

```text
controlled mixtures

LoB

LoD

LoQ

mixture fraction calibration

length-mixture candidates
```

Goal:

> Establish validated limits before quantitative heteroplasmy reporting.

---

# 127. High-Level Non-Goals

Do not prioritize the following before the scientific foundations above are complete:

```text
VCF just for format completeness

many CLI output formats

generic genome assembly

large neural models

automatic pathogenicity interpretation

clinical diagnosis

GUI-first development

microservice architecture

distributed execution

database infrastructure
```

These can be introduced only when justified by real workflow needs.

---

# 128. Final Recommendation

Signal's current architecture should not be replaced.

The project already has valuable properties that are difficult to add later:

```text
strict validation

determinism

typed stages

auditable provenance

versioned contracts

conservative biological semantics

circular mtDNA support
```

The primary change should be conceptual.

Move from:

```text
trace
  ->
primary sequence
  ->
reference differences
```

toward:

```text
sample
  ->
multiple independent traces
  ->
signal-level evidence
  ->
evidence-aware consensus
  ->
mtDNA-specific variant representation
  ->
mixed-signal evidence
  ->
phylogenetic/sample QC
```

The recommended implementation order is:

```text
Peak Evidence
    |
    v
Better Basecalling
    |
    v
ReadObservation
    |
    v
Sample Manifest
    |
    v
Sample Consensus
    |
    v
Bidirectional Variant Evidence
    |
    v
mtDNA Nomenclature / Poly-C Handling
    |
    v
Mixed-Base Candidates
    |
    v
Haplogroup QC
    |
    v
Real Validation
    |
    v
Calibrated Confidence
    |
    v
Validated Heteroplasmy
```

The single most important rule is:

> Preserve evidence first, increase biological claims only after the evidence and validation justify them.

That principle is already visible in Signal's existing design and should remain the foundation of its mtDNA evolution.
