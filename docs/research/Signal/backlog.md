# TODO — mtDNA Roadmap Prioritized by ROI

> This file prioritizes the proposed mtDNA improvements by expected return on engineering effort.
>
> ROI here means:
>
> ```text
> ROI ≈ scientific impact × product usefulness × risk reduction
>       ---------------------------------------------------------
>                  implementation effort
> ```
>
> The ordering is intentionally not the same as architectural elegance.
>
> The goal is to deliver the largest improvement in real mtDNA usefulness with the smallest amount of complexity and scientific risk.

---

# 1. Priority Model

Use the following labels throughout this roadmap.

## ROI

```text
ROI-5 = exceptional return; should be done immediately
ROI-4 = very high return
ROI-3 = good return
ROI-2 = useful but relatively expensive
ROI-1 = low near-term return / research-heavy
```

## Effort

```text
XS = < 1 focused engineering day
S  = roughly 1-3 days
M  = roughly 3-7 days
L  = roughly 1-3 weeks
XL = multi-week / research program
```

These are relative estimates, not schedule commitments.

---

# 2. ROI Summary

| Rank | Work Item                                       | ROI | Effort | Scientific Impact | Product Impact |
| ---: | ----------------------------------------------- | --: | -----: | ----------------: | -------------: |
|    1 | Peak geometry beyond the completed v3 gate      |   5 |    S-M |         Very High |           High |
|    2 | Preserve richer per-call evidence               |   5 |    S-M |         Very High |           High |
|    3 | Multi-read sample manifest                      |   5 |    S-M |              High |      Very High |
|    4 | Sample-level consensus                          |   5 |      M |         Very High |      Very High |
|    5 | Bidirectional support tracking                  |   5 |    S-M |         Very High |      Very High |
|    6 | Remove raw peak height as primary evidence gate |   5 |      S |              High |           High |
|    7 | Add per-locus local SNR / corrected amplitude   |   5 |      M |         Very High |           High |
|    8 | Sample-level coverage reporting                 |   5 |      S |              High |           High |
|    9 | Variant evidence aggregation across reads       |   5 |      M |         Very High |      Very High |
|   10 | Real AB1 regression corpus                      |   5 |    M-L |         Very High |      Very High |
|   11 | Expected-region constrained alignment           |   4 |    S-M |            Medium |           High |
|   12 | Mapping QC against expected amplicon            |   4 |      S |              High |           High |
|   13 | Homopolymer / poly-C context annotation         |   4 |    S-M |              High |           High |
|   14 | mtDNA-specific variant projection               |   4 |      M |              High |           High |
|   15 | Mixed-base candidate detection                  |   4 |    M-L |         Very High |           High |
|   16 | Better deletion evidence                        |   4 |      M |              High |         Medium |
|   17 | Immutable batch runs / resume                   |   4 |      M |               Low |      Very High |
|   18 | PLOC refinement                                 |   3 |    M-L |              High |         Medium |
|   19 | Haplogroup QC                                   |   3 |    M-L |              High |         Medium |
|   20 | Calibrated per-call confidence                  |   3 |   L-XL |         Very High |           High |
|   21 | Whole-mtGenome sample support                   |   3 |      L |              High |           High |
|   22 | Length-mixture detection                        |   2 |   L-XL |         Very High |         Medium |
|   23 | NUMT / off-target QC                            |   2 |      L |            Medium |         Medium |
|   24 | Quantitative heteroplasmy estimation            |   2 |     XL |         Very High |           High |
|   25 | ML base-call correction                         |   1 |     XL |  Potentially High |         Medium |
|   26 | End-to-end neural basecalling                   |   1 |     XL |          Research |  Low Near-Term |

---

# 3. ROI-5 — Do First

These tasks provide the largest improvement in correctness and usability for relatively little complexity.

---

## TODO 1 — Expand Peak Co-localization Beyond the Initial Gate

**ROI:** 5
**Effort:** S-M
**Priority:** Critical
**Status:** Initial conservative gate completed in `signal.peak_recall/v3`

### Completed

For a uniquely strongest positive peak, v3 requires every qualifying channel to pass `secondary_peak_ratio` both at its independently selected peak and at the primary peak sample. This rejects a remote channel maximum when that channel has insufficient signal at the primary event, while preserving primary selection, exact-tie behavior, PLOC fallback, and existing ambiguity semantics.

### Remaining Problem

The primary-sample check is deliberately narrower than a complete peak-geometry model. Broad, compressed, or overlapping neighboring peaks can still pass at one sample without representing the same nucleotide event.

### Follow-up

Evaluate explicit spatial compatibility using validated peak positions, widths, prominence, and local spacing. A possible future rule is:

```text
abs(secondary_peak_position - major_peak_position)
    <= allowed_offset
```

where `allowed_offset` is bounded and derived from validated local spacing rather than introduced as an arbitrary compatibility knob.

### Acceptance Criteria

* v3 remote-secondary and overlapping-secondary regression tests remain green;
* richer geometry is validated against synthetic and approved real traces;
* deterministic tie and primary behavior remain unchanged;
* a future method version changes calls only when secondary evidence is geometrically invalid.

---

## TODO 2 — Add Rich Per-Locus Signal Evidence

**ROI:** 5
**Effort:** S-M
**Priority:** Critical

### Goal

Stop reducing each call to:

```text
peak height
primary
ambiguity
relative quality
```

Preserve enough evidence for future:

* consensus;
* mixed-base detection;
* calibrated quality;
* artifact analysis;
* review tooling.

### Add Internal Model

```rust
pub struct CallEvidence {
    pub index_0based: usize,

    pub ploc_0based: usize,

    pub primary_peak_position_0based: usize,

    pub channel_heights: [i32; 4],

    pub channel_offsets: [i32; 4],

    pub primary_height: i32,

    pub secondary_height: Option<i32>,

    pub secondary_primary_ratio: Option<f64>,

    pub local_spacing_previous: Option<usize>,

    pub local_spacing_next: Option<usize>,
}
```

Later extend with:

```text
baseline
corrected amplitude
SNR
prominence
width
saturation
```

### Important

This is primarily an internal scientific representation.

Do not immediately bloat `signal.analysis/v5`.

### Acceptance Criteria

* every base call has deterministic evidence;
* all channel ordering remains canonical A/C/G/T;
* downstream stages can consume evidence without reading raw chromatogram arrays again;
* no current external output contract needs to change initially.

---

## TODO 3 — Add Per-Locus Corrected Signal Strength

**ROI:** 5
**Effort:** M
**Priority:** Critical

### Problem

Raw fluorescence height is instrument/run dependent.

This makes rules such as:

```toml
minimum_peak_height = 150
```

scientifically weak as the main acceptance criterion.

### Implement

For each call/channel calculate:

```text
baseline

corrected_height =
    max(0, raw_peak_height - baseline)
```

Use a robust local baseline.

First implementation may use:

```text
median(samples in local channel span)
```

### Output Internally

```rust
pub struct ChannelEvidence {
    pub raw_height: i32,
    pub baseline: f64,
    pub corrected_height: f64,
}
```

### Acceptance Criteria

* corrected values are finite;
* baseline logic is deterministic;
* decoded signal is never mutated;
* corrected height can be tested using synthetic baseline-offset traces.

---

## TODO 4 — Add Per-Locus Local SNR

**ROI:** 5
**Effort:** M
**Priority:** Critical

### Goal

Provide signal evidence that is more comparable across traces than raw fluorescence.

### Suggested Metric

Reuse the project's robust noise ideas:

```text
baseline =
    median(samples)

noise_sigma =
    MAD(first differences)
    / (0.67448975 * sqrt(2))

noise_sigma =
    max(noise_sigma, 1.0)

signal =
    max(0, peak - baseline)

snr =
    signal / noise_sigma
```

### Store

```rust
pub struct ChannelEvidence {
    ...
    pub noise_sigma: f64,
    pub snr: f64,
}
```

### Do Not

Immediately claim:

```text
SNR X means base error probability Y
```

### Acceptance Criteria

* finite results only;
* deterministic rounding rules;
* unit tests for flat signal, noisy signal, high signal, and low signal;
* SNR remains observational until calibrated.

---

## TODO 5 — Reduce Reliance on `minimum_peak_height`

**ROI:** 5
**Effort:** S
**Priority:** Critical

### Current Problem

Variant acceptance currently depends strongly on:

```text
highest raw peak >= minimum_peak_height
```

This threshold is unlikely to generalize across instruments and runs.

### Immediate Change

Do not necessarily delete the setting yet.

Change its role from:

```text
primary scientific evidence
```

to:

```text
sanity floor / legacy auxiliary filter
```

Introduce signal-based evidence:

```text
local primary SNR
corrected height
peak geometry
```

### Short-Term Filtering Policy

Prefer:

```text
supporting call must satisfy:

reasonable corrected signal
AND
reasonable local SNR
AND
acceptable quality evidence
```

### Acceptance Criteria

* variant filtering no longer relies on raw height alone;
* configuration semantics are clearly documented;
* existing results can be regression compared.

---

## TODO 6 — Add Explicit mtDNA Sample Manifest

**ROI:** 5
**Effort:** S-M
**Priority:** Critical

### Goal

Move from file-oriented processing toward biological-sample processing.

### Add Manifest

Example:

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
    expected_region:
      start: 15950
      end: 16450

  - trace: SAMPLE_001_HV1_R.ab1
    amplicon: HV1
    direction: reverse
    expected_region:
      start: 15950
      end: 16450
```

### Required Fields

```text
sample identity
trace path
direction
```

### Optional Fields

```text
amplicon
primer
expected region
replicate ID
```

### Reject

```text
duplicate trace
duplicate logical read
invalid direction
region outside reference
conflicting reference
duplicate sample ownership
```

### Acceptance Criteria

* deterministic manifest parsing;
* strict schema;
* manifest checksum recorded;
* filename conventions are not used as biological truth.

---

## TODO 7 — Build Sample-Level Consensus MVP

**ROI:** 5
**Effort:** M
**Priority:** Critical

### Goal

Aggregate multiple independently analyzed reads from one sample.

### First Version

Do not build a sophisticated probabilistic consensus yet.

Start with conservative rules.

For each reference position:

```text
collect observations
group by nucleotide
retain confidence/evidence
determine strand support
```

### Internal Model

```rust
pub struct SamplePosition {
    pub position_1based: usize,

    pub observations: Vec<ReadPositionObservation>,

    pub consensus: ConsensusCall,

    pub coverage: CoverageState,

    pub discordant: bool,
}
```

### Consensus States

```rust
pub enum ConsensusState {
    Confirmed,
    SingleDirection,
    SingleRead,
    Discordant,
    LowConfidence,
    NoCoverage,
}
```

### Acceptance Criteria

* multiple reads map into one reference coordinate space;
* reverse reads map correctly to original call indices;
* consensus never invents coverage;
* conflicting high-quality reads produce discordance rather than arbitrary majority resolution.

---

## TODO 8 — Make Bidirectional Evidence First-Class

**ROI:** 5
**Effort:** S-M
**Priority:** Critical

### Add

```rust
pub enum SupportLevel {
    SingleRead,
    SameDirectionReplicate,
    Bidirectional,
    IndependentAmplicon,
}
```

### Apply To

```text
sample consensus
SNVs
insertions
deletions
mixed-base candidates
review status
```

### Example

```json
{
  "support": {
    "level": "bidirectional",
    "forward_reads": 1,
    "reverse_reads": 1
  }
}
```

### Acceptance Criteria

* every sample-level variant knows its independent support level;
* one-strand-only findings are visibly distinguishable;
* bidirectional confirmation does not alter underlying raw read evidence.

---

## TODO 9 — Add Sample-Level Coverage

**ROI:** 5
**Effort:** S
**Priority:** Critical

### Goal

Allow the pipeline to distinguish:

```text
no variant observed
```

from:

```text
position was never observed
```

### Per-Position States

```rust
pub enum CoverageState {
    Uncovered,
    CoveredNoCall,
    SingleRead,
    SingleDirection,
    Bidirectional,
}
```

### Summary

```json
{
  "coverage": {
    "covered_positions": 790,
    "callable_positions": 772,
    "bidirectional_positions": 701,
    "single_direction_positions": 71
  }
}
```

### Acceptance Criteria

* absence of coverage is explicit;
* callable and covered are separate concepts;
* region coverage can be summarized.

---

## TODO 10 — Aggregate Variants Across Reads

**ROI:** 5
**Effort:** M
**Priority:** Critical

### Problem

A read-level difference is not the same as a sample-level variant.

### Add

```rust
pub struct SampleVariant {
    pub canonical: CanonicalVariant,

    pub read_observations: Vec<VariantObservation>,

    pub support_level: SupportLevel,

    pub review_status: VariantReviewStatus,
}
```

### Review Status

```rust
pub enum VariantReviewStatus {
    Strong,
    Supported,
    ReviewRecommended,
    InsufficientEvidence,
}
```

### Acceptance Criteria

Equivalent normalized variants from different reads must collapse into one sample variant.

Do not merge:

```text
different normalized allele
different anchor
different event class
```

unless normalization proves equivalence.

---

## TODO 11 — Build a Real AB1 Regression Corpus

**ROI:** 5
**Effort:** M-L
**Priority:** Critical

### Reason

This provides more value than adding sophisticated algorithms without knowing current real-world failure modes.

### Corpus Should Include

```text
clean forward reads
clean reverse reads
HVI
HVII
HVIII
weak signal
poor ends
homopolymers
poly-C
known SNVs
known indels
mixed signals where available
```

### For Each Approved Fixture Record

```text
AB1 checksum
instrument/run metadata when available
primer
expected region
expected orientation
reference checksum
expected base sequence
expected differences
truth source
approval status
```

### Acceptance Criteria

A release validation script should report:

```text
base agreement
mapping agreement
variant agreement
coverage
runtime
memory
```

No release claim should depend only on synthetic traces.

---

# 4. ROI-4 — High Value After the Core

---

## TODO 12 — Constrain Alignment Using Expected Amplicon

**ROI:** 4
**Effort:** S-M

### Goal

Avoid searching the entire mtDNA reference when the biological experiment already tells us where the read should be.

### Flow

```text
expected region
    +
configured margin
    |
    v
extract circular reference window
    |
    v
current deterministic alignment
```

### Example

```text
expected:
16000..16450

margin:
100

search:
15900..16550
```

### Fallback

If localized alignment fails:

```text
full circular reference search
```

### Benefits

```text
faster
less memory
less accidental placement
stronger mapping QC
```

---

## TODO 13 — Add Mapping QC

**ROI:** 4
**Effort:** S

### Warnings

```text
mapped_outside_expected_region
unexpected_orientation
low_identity
unexpected_origin_wrap
mapping_far_from_primer
ambiguous_mapping
```

### Acceptance Criteria

Mapping QC must not silently change calls.

It should annotate:

```text
unexpected but accepted
```

versus:

```text
analysis failure
```

with clear policy.

---

## TODO 14 — Add Homopolymer and Poly-C Context Annotation

**ROI:** 4
**Effort:** S-M

### Add

```rust
pub struct SequenceContext {
    pub homopolymer_base: Option<Nucleotide>,
    pub homopolymer_length: usize,
    pub repeat_context: bool,
    pub control_region_poly_c: bool,
}
```

### Attach To

```text
indels
mixed signals
review status
length-mixture candidates
```

### Why

This gives immediate scientific value without needing to solve length heteroplasmy yet.

---

## TODO 15 — Add mtDNA Variant Projection

**ROI:** 4
**Effort:** M

### Preserve

Current canonical normalized representation.

### Add

A separate mtDNA-facing representation.

```text
canonical variant
    |
    v
mtDNA nomenclature projection
```

### Example

```json
{
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
```

### Important

Never move mtDNA naming rules into generic alignment code.

---

## TODO 16 — Improve Deletion Evidence

**ROI:** 4
**Effort:** M

### Current Weakness

Deletion filtering does not have direct supporting query bases and is therefore relatively permissive.

### Add Evidence

```text
left flank quality
right flank quality
local SNR
alignment stability
homopolymer context
bidirectional confirmation
```

### Model

```rust
pub struct DeletionEvidence {
    pub left_flank: Option<CallEvidenceSummary>,
    pub right_flank: Option<CallEvidenceSummary>,
    pub repeat_context: bool,
    pub support_level: SupportLevel,
}
```

---

## TODO 17 — Mixed-Base Candidate Detection

**ROI:** 4
**Effort:** M-L

### Important Semantic Rule

Call this:

```text
mixed_base_candidate
```

not:

```text
heteroplasmy
```

### Requirements

Minor signal should satisfy:

```text
co-localization
sufficient corrected amplitude
sufficient local SNR
reasonable peak geometry
```

### Aggregate Across Reads

Strongest category:

```text
same major/minor pair
seen in forward
seen in reverse
similar local behavior
```

### Example

```json
{
  "position": 152,
  "classification": "mixed_base_candidate",
  "major": "A",
  "minor": "G",
  "evidence": {
    "minor_major_ratio": 0.24,
    "major_snr": 20.1,
    "minor_snr": 7.2,
    "bidirectional": true
  }
}
```

---

## TODO 18 — Immutable Batch Runs

**ROI:** 4
**Effort:** M

### Replace

```text
delete selected old outputs
rerun
```

with:

```text
new immutable run directory
```

### Example

```text
runs/
└── RUN_ID/
    ├── run.json
    ├── logs/
    ├── reads/
    └── samples/
```

### Add

```text
run ID
resume
retry failed
complete/incomplete status
```

### Acceptance Criteria

Successful outputs are never overwritten.

---

# 5. ROI-3 — Valuable, but Do After the Core

---

## TODO 19 — PLOC Refinement

**ROI:** 3
**Effort:** M-L

### Goal

Turn vendor PLOC into a prior instead of a fixed locus.

### First Version

Search a bounded radius:

```text
PLOC ± 2-3 samples
```

Choose refined position using:

```text
composite signal
local peak shape
neighbor spacing
```

### Critical Rule

Never allow refinement to cross neighboring locus boundaries.

### Measure

Compare against:

```text
vendor PLOC
manual truth
known sequence
```

---

## TODO 20 — Haplogroup QC

**ROI:** 3
**Effort:** M-L

### Use Case

Primarily:

```text
sample QC
```

not variant correction.

### Add Versioned Resource

```text
resource name
version
checksum
```

### Output

```text
best assignment
resolution
alternative assignments
missing expected markers
unexpected markers
conflicts
```

### Rule

Never overwrite a strong signal-derived allele because the tree expects another state.

---

## TODO 21 — Calibrated Per-Call Confidence

**ROI:** 3
**Effort:** L-XL

### Target

Estimate:

```text
P(call is correct)
```

or:

```text
P(call is wrong)
```

### Requires

Independent truth corpus.

### Candidate Features

```text
corrected peak heights
local SNR
secondary ratio
peak offsets
spacing
prominence
baseline
noise
read position
artifact flags
```

### Evaluate

```text
Brier score
log loss
calibration curve
false high-confidence error rate
```

---

## TODO 22 — Whole-mtGenome Sample Support

**ROI:** 3
**Effort:** L

### Requires

Sample-level consensus first.

### Add

```text
multi-amplicon assembly
overlap consensus
gap detection
whole-genome coverage
cross-amplicon conflicts
```

### Important

Do not treat this as:

```text
regions = [[1,16569]]
```

only.

---

# 6. ROI-2 — Research-Heavy / Later

---

## TODO 23 — Length-Mixture Detection

**ROI:** 2
**Effort:** L-XL

### Goal

Detect signal patterns consistent with length mixture.

### Expected Pattern

```text
clean pre-event trace
        |
        v
length difference
        |
        v
persistent phase-shifted mixed signal
```

### Potential Evidence

```text
abrupt onset
persistent double peaks
consistent phase shift
homopolymer context
repeat across directions
```

### Initial Output

```text
length_mixture_candidate
```

not quantified heteroplasmy.

---

## TODO 24 — NUMT / Off-Target QC

**ROI:** 2
**Effort:** L

### Possible Inputs

```text
primer sequence
expected amplicon
optional nuclear reference
known NUMT resources
```

### Possible Warnings

```text
possible_numt_interference
possible_off_target_amplification
possible_mixed_template
```

### Important

This is QC assistance, not proof.

---

## TODO 25 — Quantitative Heteroplasmy

**ROI:** 2
**Effort:** XL

### Do Not Start Until

```text
mixed-base candidate detection works
controlled mixtures exist
real validation corpus exists
bidirectional consensus exists
```

### Must Establish

```text
LoB
LoD
LoQ
```

### Output States

```text
not evaluated
below validated detection
detected but not quantifiable
quantifiable
```

---

# 7. ROI-1 — Avoid for Now

---

## TODO 26 — ML Base-Call Correction

**ROI:** 1
**Effort:** XL

Do only after calibrated confidence demonstrates where deterministic basecalling fails.

Prefer shadow mode first:

```text
current call
ML suggested call
agreement
truth
```

Do not replace deterministic calls until validated.

---

## TODO 27 — End-to-End Neural Basecalling

**ROI:** 1
**Effort:** XL

Low priority because Signal currently benefits more from:

```text
better evidence
sample consensus
real validation
mixed-signal analysis
```

An end-to-end model would also increase:

```text
training-data requirements
reproducibility complexity
model provenance burden
domain-shift risk
```

---

# 8. Recommended Execution Order

Use this sequence unless real validation reveals a higher-severity issue.

```text
1. Peak geometry beyond the completed v3 gate
        |
        v
2. Rich call evidence
        |
        v
3. Corrected amplitude + local SNR
        |
        v
4. Reduce raw-height filtering
        |
        v
5. Sample manifest
        |
        v
6. Sample consensus
        |
        v
7. Bidirectional support
        |
        v
8. Coverage
        |
        v
9. Sample variant aggregation
        |
        v
10. Real AB1 regression corpus
        |
        v
11. Expected-region alignment
        |
        v
12. Mapping QC
        |
        v
13. Homopolymer/poly-C context
        |
        v
14. mtDNA nomenclature
        |
        v
15. Mixed-base candidates
        |
        v
16. Better deletion evidence
        |
        v
17. Immutable batch execution
        |
        v
18. PLOC refinement
        |
        v
19. Haplogroup QC
        |
        v
20. Calibrated call confidence
        |
        v
21. Whole-mtGenome support
        |
        v
22. Length-mixture research
        |
        v
23. NUMT QC
        |
        v
24. Quantitative heteroplasmy
```

---

# 9. Recommended Near-Term Milestone

The highest-ROI milestone is:

```text
Signal mtDNA MVP
```

It should include:

```text
[x] single-read deterministic analysis
[x] initial primary-sample peak co-localization
[ ] spacing-aware peak geometry
[ ] richer call evidence
[ ] local corrected signal / SNR
[ ] explicit sample manifest
[ ] multiple reads per sample
[ ] forward/reverse consensus
[ ] sample coverage
[ ] sample-level variants
[ ] bidirectional support
[ ] real-trace regression tests
```

This is enough to move Signal from:

```text
trace analyzer
```

to:

```text
useful mtDNA Sanger sample analyzer
```

without making premature heteroplasmy claims.

---

# 10. Suggested First Four PRs

## PR 1 — Expand Secondary Peak Geometry

Build on the completed v3 primary-sample gate and deliver:

```text
spacing-aware peak compatibility
channel peak offsets and widths
approved real-trace validation
```

ROI:

```text
extremely high
```

because it can directly reduce false mixed signals and false ambiguities.

---

## PR 2 — Add Call Evidence v1

Deliver:

```text
corrected height
local SNR
peak ratio
peak offsets
local spacing
```

No major external contract change required initially.

---

## PR 3 — Add mtDNA Manifest + Sample Model

Deliver:

```text
strict manifest
read metadata
direction
amplicon
expected region
sample identity
```

No consensus yet.

---

## PR 4 — Sample Consensus + Variant Aggregation

Deliver:

```text
coordinate aggregation
coverage
forward/reverse support
sample consensus
sample variants
sample JSON
```

This PR provides the largest product-level jump.

---

# 11. Suggested Definition of `v0.2`

`v0.2` should prioritize high ROI rather than feature count.

Recommended scope:

```text
spacing-aware peak geometry beyond v3
per-call evidence
local SNR
sample manifest
sample consensus
bidirectional support
coverage
sample-level variants
```

Do not include yet:

```text
heteroplasmy %
haplogroup correction
ML calling
whole-genome assembly
NUMT classification
```

---

# 12. Suggested Definition of `v0.3`

Recommended:

```text
expected-region alignment
mapping QC
homopolymer/poly-C context
mtDNA nomenclature
mixed-base candidates
better deletion evidence
immutable batch runs
```

---

# 13. Suggested Definition of `v0.4`

Recommended:

```text
PLOC refinement
haplogroup QC
larger real validation corpus
calibrated call confidence
whole-mtGenome sample orchestration
```

---

# 14. Scientific Gates

Some tasks must not begin merely because engineering bandwidth exists.

---

## Gate A — Before Mixed-Base Candidate Detection

Require:

```text
peak co-localization implemented
local SNR implemented
signal evidence preserved
```

---

## Gate B — Before Quantitative Heteroplasmy

Require:

```text
mixed-base candidate detector validated
controlled mixture samples
bidirectional processing
independent truth
LoB/LoD/LoQ study
```

---

## Gate C — Before ML Call Correction

Require:

```text
large truth corpus
grouped train/test splits
calibrated deterministic baseline
clear target metric
```

---

## Gate D — Before Whole mtGenome Release

Require:

```text
sample-level consensus
multiple amplicons
overlap handling
coverage/gap reporting
cross-amplicon conflict handling
```

---

# 15. Things That Look Valuable but Should Wait

Do not spend near-term engineering effort on:

```text
VCF output
FASTQ output
large GUI
REST API
database backend
cloud orchestration
microservices
GPU inference
full neural basecaller
clinical pathogenicity annotation
```

unless a concrete user workflow requires them.

Their ROI is currently lower than fixing the scientific core.

---

# 16. High-ROI Testing Tasks

Testing itself has very high ROI.

Prioritize:

```text
[x] synthetic non-colocalized secondary peaks
[x] co-localized mixed peaks
[ ] strong baseline drift
[ ] weak signal
[ ] saturated peaks
[ ] compressed spacing
[ ] reverse-read coordinate mapping
[ ] bidirectional variant confirmation
[ ] conflicting forward/reverse calls
[ ] homopolymer indel
[ ] circular origin alignment
[ ] sample with missing reverse read
[ ] sample with overlapping amplicons
```

---

# 17. High-ROI Documentation Tasks

Low engineering effort, meaningful future risk reduction.

```text
[ ] explicitly document raw peak height as non-portable
[ ] explicitly document relative quality as within-read only
[ ] document read-level vs sample-level difference
[ ] document mixed-base candidate vs heteroplasmy
[ ] document bidirectional support semantics
[ ] document coverage vs callable coverage
[ ] document canonical variant vs mtDNA display notation
```

---

# 18. ROI Decision Rules for Future Work

When evaluating a new task, ask:

### Does it improve correctness of current outputs?

If yes:

```text
high ROI
```

---

### Does it convert read-level data into sample-level biological evidence?

If yes:

```text
high ROI
```

---

### Does it reduce false mixed-signal or false variant interpretation?

If yes:

```text
high ROI
```

---

### Does it require large training datasets before providing value?

If yes:

```text
usually lower near-term ROI
```

---

### Is it primarily a new format or presentation layer?

If yes:

```text
lower ROI unless directly required by users
```

---

### Does it increase biological claims without stronger evidence?

If yes:

```text
do not prioritize
```

---

# 19. Current Best ROI Allocation

If engineering capacity is limited to roughly four major units of work, allocate it as:

```text
30%  peak and signal evidence
30%  sample consensus
20%  variant aggregation + bidirectional evidence
20%  real validation
```

Do not allocate significant effort yet to:

```text
ML
heteroplasmy quantification
haplogroup sophistication
whole-mtGenome optimization
```

---

# 20. Final Priority Order

The practical ordering is:

```text
P0 / ROI-5
    Peak geometry beyond the completed v3 gate
    Rich call evidence
    Local corrected amplitude/SNR
    Reduce raw-height dependence
    Sample manifest
    Sample consensus
    Bidirectional support
    Coverage
    Sample-level variants
    Real validation

P1 / ROI-4
    Expected-region alignment
    Mapping QC
    Homopolymer/poly-C context
    mtDNA nomenclature
    Mixed-base candidates
    Better deletion evidence
    Immutable batch runs

P2 / ROI-3
    PLOC refinement
    Haplogroup QC
    Calibrated confidence
    Whole-mtGenome support

P3 / ROI-2
    Length-mixture detection
    NUMT QC
    Quantitative heteroplasmy

P4 / ROI-1
    ML base correction
    End-to-end neural basecalling
```

The highest-return strategy is therefore:

> First improve the quality of the evidence, then combine independent reads into sample-level evidence, then expand mtDNA interpretation.

That ordering gives Signal the biggest improvement in real scientific usefulness without prematurely increasing complexity or biological claims.
