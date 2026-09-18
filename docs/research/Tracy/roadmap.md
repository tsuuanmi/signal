# Tracy Research Roadmap

This roadmap is a sequencing of research and validation work, not a commitment to ship every phase. The 2026-09 source/issue audit adds an evidence-foundation gate before profile work.

## Phase 0 — protect the evidence foundation

Before changing alignment semantics:

```text
mixed-supporting-call gate for simple variants
PLOC completeness/suspicion diagnostics
artifact test corpus
saturation/high-amplitude-outlier observations
baseline-shift and neighbor-interference cases
```

This phase is intentionally conservative. It should improve trust in existing
single-trace output without requiring profile alignment.

## Phase A — richer locus evidence

Research and validate:

```text
baseline/corrected height
prominence
local noise
per-channel SNR
spacing-aware co-localization beyond the v3 sample gate
bounded locus refinement
explicit artifact flags
```

Output:

```text
LocusEvidence
```

Observed values and derived interpretations remain separate.

## Phase B — basecall-independent evidence profile

Implement:

```text
LocusEvidence
    ->
EvidenceProfile
```

The profile must derive from channel evidence directly. It must not be defined
by which channels already passed the current ambiguity threshold.

Initially keep primary calling unchanged to isolate profile behavior.

## Phase C — profile/reference alignment

Add an experimental evidence-aware substitution scorer around the existing
Gotoh state machine.

Define before implementation:

```text
fixed numeric/quantization policy
unresolved evidence score
orientation tie semantics
gap semantics
circular topology behavior
identity/callable metrics
```

Benchmark against current primary-sequence Gotoh and protect origin-crossing
circular cases.

## Phase D — ReadObservation

Map each accepted trace into immutable reference-coordinate observations.

This layer preserves:

```text
trace identity
orientation
source call/PLOC mapping
nucleotide evidence
local quality/artifact state
alignment/gap observations
```

Reference-aware interpretation cannot rewrite the source evidence.

## Phase E — generic sample-evidence reconciliation

Implement the generic N-read aggregation model first. Validate it initially with
the simplest two-read F/R case, but do not encode "pair" as the domain boundary.

Start validation with one forward and one reverse trace.

Before consensus:

```text
minimum overlap
minimum agreement/read admission
orientation confidence
artifact/quality admission
```

At each locus preserve both nucleotide evidence and explicit gap/indel event
support. High-quality conflicts remain visible.

The same implementation must also accept partial/tiled sets such as HV1F,
HV1R, HV2F, HV3R and allow any reads that overlap the same reference event to
contribute.

## Phase F — reference-guided multi-read consensus

Generalize to replicates and overlapping amplicons.

Add:

```text
manifest/sample identity
read admission
local coverage denominator
independent-strand support
coverage map
evidence-weighted consensus
sample-level candidate variants
```

Do not use Tracy-style quality-blind majority voting as the final decision rule.

## Phase G — persistent mixed-signal / length-mixture detection

Implement observation-only:

```text
signal-cleanliness metric
change-point search
candidate +/-N phase shifts
reference-consistency ranking
alignment-stability evidence
```

Return a new hypothesis object. Never mutate primary/secondary evidence to fit a
reference-threading hypothesis.

## Phase H — mtDNA-specific interpretation

Add downstream context:

```text
poly-C/repeat context
mtDNA nomenclature projection
haplogroup consistency QC
```

These remain downstream of generic signal and alignment evidence.

## Optional scaling phase — large-reference candidate placement

This phase is not on the current mtDNA path.

Only if reference scope grows beyond bounded direct alignment:

~~~text
query evidence
  -> candidate search/index
  -> candidate regions
  -> authoritative evidence-aware alignment
~~~

Validation must report candidate-search recall separately from final alignment
correctness. Circular topology and ambiguous placements remain explicit.

## Phase I — calibration

Only after sufficient truth data:

```text
calibrated call confidence
validated mixed-base detection
validated sample consensus confidence
validated heteroplasmy estimation
assay-specific LoD/LoQ
```

## Updated priority view

| Priority | Improvement | Expected ROI | Effort |
|---|---|---:|---:|
| P0 | mixed-supporting-call simple-variant gate | Very high | Low |
| P0 | PLOC completeness + artifact validation | Very high | Low-Medium |
| P0 | richer `LocusEvidence` / peak geometry | Very high | Medium |
| P0 | basecall-independent evidence profile | Very high | Medium |
| P0 | evidence-aware Gotoh scorer | Very high | Medium |
| P1 | explicit read admission / overlap policy | High | Low-Medium |
| P1 | generic N-read evidence reconciliation, F/R as first validation case | Very high | Medium-High |
| P1 | reference-guided multi-read consensus | Very high | Medium-High |
| P1 | change-point length-mixture detection | High | Medium |
| P1 | candidate +/-N phase-shift evaluation | High | Medium |
| P1 | poly-C/repeat context | High | Medium |
| P2 | multi-amplicon whole-mtDNA consensus | High | High |
| P2 | review/evidence artifact | Medium-High | Medium |
| P3 | VCF/BCF projection | Medium | Low-Medium |
| Defer | quantitative heteroplasmy | Potentially high | Very high |
| Skip now | FM-index / large-reference candidate search | Very low for current scope | High |
| Skip now | direct de novo assembly port | Very low | High |

## Highest-value Tracy lessons after the source audit

If Signal adopts only a few concepts, they should be:

1. keep nucleotide evidence through alignment and consensus;
2. validate the evidence foundation before adding sophisticated downstream interpretation;
3. use persistent post-indel phase shifts as hypotheses, not automatic diploid calls;
4. preserve coordinate provenance so every result remains traceable to the chromatogram.

The source audit also identifies what not to inherit: basecall-gated profiles,
quality-blind multi-trace voting, uncalibrated likelihood terminology, reference
mutation of observed calls, and linear-reference assumptions.
