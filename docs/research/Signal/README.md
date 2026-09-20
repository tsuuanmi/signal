# Signal Research

This subtree contains Signal-specific exploratory work that has not yet been promoted into the root production contract.

- [backlog.md](backlog.md): research and ROI backlog previously kept in `docs/TODO.md`.
- [improvement-plan.md](improvement-plan.md): detailed exploratory mtDNA improvement plan previously kept in `docs/UPDATE.md`.
- [validation-corpus.md](validation-corpus.md): corpus strata, truth/provenance, replication, privacy, anti-leakage design, and implemented manifest-driven local orchestration.
- [threshold-research.md](threshold-research.md): LoB/LoD-style profile-geometry threshold research protocol and promotion gates.
- [validation-measurements.md](validation-measurements.md): deterministic per-locus measurement export used by local threshold analysis.
- [research-dataset.md](research-dataset.md): implemented hash-bound joined locus/observation tables and descriptive geometry summaries before threshold selection.
- [audit-strata.md](audit-strata.md): implemented observational read/locus/case review strata for corpus curation without truth assignment or production QC.
- [curation-queue.md](curation-queue.md): immutable audit-supported human-review queue plus separate editable decisions template before manifest reconciliation.
- [polyc-phase-instability.md](polyc-phase-instability.md): directional rCRS HV1/HV2 poly-C crossing dataset for descriptive phase-instability and recovery research without production confidence changes.
- [polyc-orientation-controls.md](polyc-orientation-controls.md): same-case, same-locus N-read controls comparing post-tract evidence with opposite selected-orientation pre-tract evidence without pair selection or thresholds.
- [polyc-phase-hypotheses.md](polyc-phase-hypotheses.md): Tracy-inspired downstream candidate-offset curves that separate shifted-reference explainability from unexplained profile residual without selecting a winning phase.
- [polyc-phase-characterization.md](polyc-phase-characterization.md): descriptive adjacent-window persistence, exact-distance trajectories, and observed-interrupt strata over complete phase-hypothesis curves without candidate selection or thresholds.
- [polyc-phase-sensitivity.md](polyc-phase-sensitivity.md): full-factorial window/stride/offset sensitivity over the authoritative phase candidate engine without selecting a preferred parameter set.
- [polyc-phase-explainability.md](polyc-phase-explainability.md): threshold-free candidate-envelope summaries for finding windows/reads whose impurity remains poorly described across all tested offsets without assigning a state.
- [polyc-phase-recurrent-loci.md](polyc-phase-recurrent-loci.md): exact recurrent-locus membership and complete candidate context for positions 253/297/302/16194/16197 without interval approximation, scoring, or truth labels.
- [phase-runtime-parity.md](phase-runtime-parity.md): completed 89-case Rust/Python `signal.polyc_phase/v1` measurement-parity evidence, including exact structural parity and numerical agreement before any interpretation policy.
- [polyc-phase-interpretation-study.md](polyc-phase-interpretation-study.md): development/holdout study design for window/tract phase-evidence interpretation, including strict Python-research/Rust-production ownership and separate later weighting promotion.
- [polyc-phase-interpretation-dataset.md](polyc-phase-interpretation-dataset.md): implemented provenance-strict development-only join of corpus metadata and production-v1 phase candidates, with aggregate holdout readiness counts but no holdout phase features or thresholds.
- [event-position-diagnostics.md](event-position-diagnostics.md): validation study for explaining primary-basecall versus continuous-profile event placement before threshold fitting.
- [variant-profile-evaluation.md](variant-profile-evaluation.md): reviewer-derived sample variant-profile baseline, explicit Sequencher notation semantics, FP/FN accounting, representation-equivalence handling, and non-regression objective before phase-aware calling.
- [variant-phase-context.md](variant-phase-context.md): development-only join of biological missing/extra variant disagreements to exact post-poly-C read/window/candidate evidence, with representation rows excluded and holdout limited to readiness counts.

These documents may contain useful ideas, hypotheses, candidate algorithms, and delivery sequences. They are not authority for current production behavior.

Promotion follows [documentation governance](../../governance/documentation.md).
