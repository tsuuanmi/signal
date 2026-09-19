# Tracy Research

This directory is the structured research documentation for what Signal can learn from [gear-genomics/tracy](https://github.com/gear-genomics/tracy).

It intentionally mirrors the organization of the root Signal documentation: requirements, architecture, ADRs, validation, roadmap, implementation notes, and focused method documents. These files are **research design**, not current production behavior. A research decision becomes normative only when it is promoted into the root Signal requirements/ADR/schema set and implemented.

## Status — production-learning phase closed

The Tracy comparison phase is closed as of 2026-09-20. The high-value lessons that fit Signal's current short-reference mtDNA scope have either been promoted into the root production architecture or deliberately deferred.

Promoted work now includes:

- mixed-signal-aware simple-SNV eligibility;
- explicit PLOC/trace-integrity evidence;
- basecall-independent A/C/G/T `EvidenceProfile`;
- fixed-point profile-aware placement;
- evidence-derived orientation and covered span;
- independent per-trace processing followed by generic N-read reference-coordinate reconciliation;
- pairwise overlap/admission evidence without pair-first F/R merging;
- coverage, variant, and differential-locus support topology;
- structural nucleotide contribution plus threshold-free profile aggregation/geometry;
- reviewer-facing differential-locus A/C/G/T profile/noisy context via ADR-0053 / `signal.sample_evidence/v8`;
- local validation/audit/curation infrastructure for later threshold research.

The remaining Tracy-inspired topics are no longer blockers for this phase. Persistent mixed-signal/phase-shift detection, poly-C recovery, calibrated weighting/consensus, large-reference search, VCF/BCF projection, and quantitative heteroplasmy belong to separate research tracks with their own validation requirements.


## Requirements and architecture

- [`requirements.md`](requirements.md): Tracy-informed research SRS.
- [`architecture.md`](architecture.md): proposed architecture and dependency boundaries.
- [`adr/README.md`](adr/README.md): research architecture decisions.
- [`implementation.md`](implementation.md): incremental PR and module plan.

## Method research

- [`overview.md`](overview.md): Tracy context and current Signal overlap.
- [`source-audit.md`](source-audit.md): source- and issue-level audit of Tracy's actual algorithms, edge cases, and operational limitations.
- [`features/locus-evidence.md`](features/locus-evidence.md): peak geometry, co-localization, and locus refinement.
- [`features/evidence-profiles.md`](features/evidence-profiles.md): preserving per-locus A/C/G/T evidence.
- [`features/profile-alignment.md`](features/profile-alignment.md): profile-to-reference and profile-to-profile alignment.
- [`features/reference-placement.md`](features/reference-placement.md): candidate reference search, topology, and placement/alignment boundaries.
- [`features/sample-analysis.md`](features/sample-analysis.md): ReadObservation, read admission, and sample-level consensus.
- [`features/read-reconciliation.md`](features/read-reconciliation.md): independent per-trace processing and coordinate/event-based multi-read reconciliation.
- [`features/mixed-signal-indels.md`](features/mixed-signal-indels.md): persistent mixed signal, indel shifts, and homopolymer context.
- [`features/multi-amplicon-consensus.md`](features/multi-amplicon-consensus.md): tiled mtDNA reads, sample-level variants, and calibration boundaries.
- [`deferred.md`](deferred.md): Tracy capabilities intentionally not prioritized.

## Planning and evidence

- [`roi.md`](roi.md): compact ROI ranking.
- [`validation.md`](validation.md): validation ladder and adversarial benchmark strategy.
- [`roadmap.md`](roadmap.md): staged research order.
- [`references.md`](references.md): Tracy source areas, paper, issues, and Signal mappings.

## Research question

> Which Tracy ideas improve biological correctness or preserve useful chromatogram evidence without weakening Signal's deterministic, typed, auditable design?

The goal is not feature parity and not a Rust port of Tracy. The main lesson is to retain useful A/C/G/T evidence beyond the primary call and introduce new interpretation only behind explicit biological and engineering contracts.

## Current research conclusions

The source audit sharpens the original direction:

1. preserve mixed evidence instead of overcalling simple variants;
2. make the PLOC dependency explicit and detect suspicious/incomplete event anchors;
3. validate artifact resilience before relying on richer downstream profiles;
4. construct profiles from channel evidence rather than thresholded basecall membership;
5. reuse Signal's deterministic Gotoh core but define profile scoring numerics/ties explicitly;
6. keep pairwise and multi-trace consensus evidence-aware and gap-aware;
7. never mutate observed basecall evidence using a reference-derived hypothesis;
8. separate candidate reference placement from authoritative alignment if large-reference search is ever added;
9. keep reference guidance distinct from observed sample support;
10. process every trace independently before any sample-level merge;
11. reconcile all overlapping reads by coordinate/event rather than pre-merging F/R pairs;
12. treat consensus sequence as a projection of sample evidence, not the source of sample variants;
13. derive each read's orientation and covered reference span from alignment evidence rather than assay labels;
14. preserve Signal's existing strengths in circular topology, normalization, typed provenance, and conservative biological semantics.

## Core principle

> Primary sequence should remain one interpretation of the chromatogram, not the only representation of the chromatogram.
