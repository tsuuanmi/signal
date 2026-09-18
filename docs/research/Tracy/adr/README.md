# Tracy Research Architecture Decision Records

These ADRs govern the Tracy research direction only. They do not change production Signal behavior until a corresponding root-level ADR/SRS change is accepted and implemented.

| ADR | Status | Decision |
|---|---|---|
| [0001](0001-preserve-evidence-beyond-primary-calls.md) | Accepted for research | Preserve chromatogram evidence beyond the primary call. |
| [0002](0002-reuse-gotoh-with-pluggable-scoring.md) | Accepted for research | Reuse one Gotoh core and generalize substitution scoring. |
| [0003](0003-layer-sample-analysis-above-single-trace-core.md) | Accepted for research | Layer sample consensus above the single-trace core. |
| [0004](0004-do-not-port-diploid-semantics-to-mtdna.md) | Accepted for research | Do not directly port Tracy's diploid interpretation to mtDNA. |
| [0005](0005-reference-guided-consensus-before-de-novo.md) | Accepted for research | Prefer reference-guided multi-trace consensus before de novo assembly. |
| [0006](0006-separate-research-evidence-contracts.md) | Accepted for research | Keep bulk research evidence outside compact production result schemas. |
| [0007](0007-reference-interpretation-must-not-mutate-observed-evidence.md) | Accepted for research | Keep observed chromatogram evidence immutable under reference-aware interpretation. |
| [0008](0008-consensus-must-remain-evidence-and-gap-aware.md) | Accepted for research | Do not collapse multi-read evidence into quality-blind character voting; model gaps explicitly. |
| [0009](0009-ploc-is-an-explicit-external-prior.md) | Accepted for research | Treat PLOC as an explicit external event prior and diagnose incompleteness. |
| [0010](0010-artifact-resilience-before-richer-interpretation.md) | Accepted for research | Validate artifact resilience before promoting richer profile-based interpretation. |

| [0011](0011-reference-guides-coordinates-but-does-not-vote.md) | Accepted for research | Use reference for coordinates/context, not as an implicit sample observation. |
| [0012](0012-candidate-placement-is-not-authoritative-alignment.md) | Accepted for research | Keep future indexed/seeded candidate search separate from final scientific alignment. |
