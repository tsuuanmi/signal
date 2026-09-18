# Tracy Research Notes

This directory contains curated research and design notes about what Signal can
learn from [gear-genomics/tracy](https://github.com/gear-genomics/tracy) and how
those ideas could fit Signal's current Rust architecture.

These notes are **non-normative**. They describe future directions, not current
Signal behavior. Current behavior remains defined by the Rust source,
[`../../pipeline.md`](../../pipeline.md), [`../../architecture.md`](../../architecture.md),
and the versioned output schemas.

The existing [`../../tracy_review.md`](../../tracy_review.md) remains the
long-form source review. This directory is the shorter decision-oriented layer.

## Research question

The useful question is not "which Tracy features can Signal copy?" It is:

> Which Tracy ideas improve biological correctness or preserve useful signal
> evidence without weakening Signal's deterministic, typed, auditable design?

Signal already covers much of Tracy's low-level foundation: ABIF decoding,
PLOC-based re-calling, primary and ambiguity calls, end trimming, affine-gap
alignment, orientation selection, and SNV/small-indel extraction. The highest
value therefore comes from the parts of Tracy that keep chromatogram evidence
alive beyond basecalling.

## Core lesson

Tracy frequently reasons with nucleotide profiles rather than reducing every
locus immediately to one base. Signal already retains channel peaks, ambiguity,
local SNR observations, call coordinates, and quality evidence, but its current
reference path ultimately aligns the retained primary sequence.

The main research direction is therefore:

```text
chromatogram
    |
    v
base calls + signal evidence
    |
    +------------------+
    |                  |
    v                  v
primary sequence   evidence profile
    |                  |
    |             evidence-aware
    |               alignment
    |                  |
    +---------+--------+
              |
              v
       variant evidence
```

Primary sequence remains useful, but it should be one interpretation of the
chromatogram rather than the only downstream representation.

## Documents

- [`roi.md`](roi.md): features and ideas ranked by expected return on investment.
- [`implementation.md`](implementation.md): how the high-ROI ideas map onto
  Signal's current modules and an incremental PR sequence.
- [`../../tracy_review.md`](../../tracy_review.md): detailed source-level review.

## Principles

1. **Preserve evidence before adding interpretation.** Prefer richer typed
   evidence over early genotype, heteroplasmy, or clinical claims.
2. **Improve the single-trace core before adding sample-level complexity.**
3. **Do not inherit Tracy's diploid assumptions for mtDNA.**
4. **Keep current production schemas stable until a feature has a validated
   contract and biological meaning.**
5. **Prefer small independent PRs with measurable biological or engineering
   benefit over a Tracy-sized feature port.**
6. **Keep deterministic behavior, explicit coordinate mappings, bounded
   algorithms, and typed invariants.**

## Recommended sequence

```text
1. Mixed/ambiguity evidence in simple-variant eligibility
2. Evidence profile model
3. Evidence-aware alignment
4. Forward/reverse trace reconciliation
5. Reference-guided multi-trace sample consensus
6. Mixed-signal / post-indel shift research
7. Optional derived interoperability outputs
```

Genome-scale indexing, de novo assembly, SCF support, genotype decomposition,
and VCF/BCF are not current priorities unless a concrete Signal use case makes
their value exceed their complexity.
