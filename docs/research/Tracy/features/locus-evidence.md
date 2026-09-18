# Locus Evidence and Peak Geometry

## 5. Window-Wide Peak Limitation and the Initial Signal Fix

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

## 6. Priority 0: Formalize Locus Evidence

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

## 7. Peak Co-Localization

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

## 8. Locus Refinement

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
