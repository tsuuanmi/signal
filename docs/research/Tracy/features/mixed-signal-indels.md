# Mixed Signal, Indel Shifts, and Homopolymers

## 31. Priority 1: Mixed-Signal Candidate Detection

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

## 32. Mixed-Base Evidence

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

## 33. Priority 1: Learn From Tracy's Indel-Shift Detection

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

## 34. Tracy's Breakpoint Concept

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

## 35. Signal Phase-Stability Metrics

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

## 36. Change-Point Detection

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

## 37. LengthMixtureCandidate

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

## 38. Priority 1: Evaluate Candidate Phase Shifts

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

## 39. PhaseShiftHypothesis

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

## 40. Robust Candidate Selection

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

## 41. Do Not Copy Tracy's Diploid Interpretation

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

## 42. Poly-C and Homopolymer Context

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

## 43. Alignment Stability Around Indels

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
