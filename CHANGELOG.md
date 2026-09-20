# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Breaking Changes

- Replace research-only `signal.validation_polyc_orientation_controls/v1` with v2, preserving each read's aligned interrupt base and deterministic post/control interrupt-base signatures directly in the control artifact without a v1 compatibility path.

- Replace `signal.sample_evidence/v7` with `signal.sample_evidence/v8`, adding required differential-locus support topology and per-call optional reference-oriented A/C/G/T evidence profiles plus noisy-region context without v7 compatibility output.

- Replace `signal.sample_evidence/v6` with `signal.sample_evidence/v7`, adding required normalized-variant support topology across read eligibility and selected orientation without v6 compatibility output.
- Replace `signal.sample_evidence/v5` with `signal.sample_evidence/v6`, adding required run-length reference coverage topology with total/forward/reverse read depth and no v5 compatibility output.
- Replace `signal.analysis/v6`, `signal.basecalls/v1`, and `signal.sample_evidence/v4` with v7/v2/v5 contracts that preserve concise PLOC/vendor cardinality, PLOC-spacing, exact clipping, and event-signal-scale integrity evidence without compatibility aliases.
- Replace strict configuration schema version 4 with version 5, requiring Tracy-derived sample-reconciliation overlap/admission thresholds.
- Replace `signal.sample_evidence/v3` with `signal.sample_evidence/v4`, adding deterministic pairwise overlap/admission evidence for independently placed reads without retaining v3 compatibility output.
- Replace `signal.sample_evidence/v2` with `signal.sample_evidence/v3` so observed SNV support can expose the new closed-enum exclusion reason `mixed_supporting_signal`; no v2 compatibility output is retained.
- Replace `signal.analysis/v5` with `signal.analysis/v6`: variant-associated calls now expose only reference-oriented `base`, co-located A/C/G/T `peaks`, and uncalibrated `quality`; original call index, mapped call position, PLOC, trace-strand symbols, and maximum-peak-only summaries are removed without compatibility output.
- Replace `signal.sample_evidence/v1` with compact `signal.sample_evidence/v2`: factor read name/SHA/orientation/coverage into one SHA-sorted read registry, replace dense `loci[]` with sparse `locus_differences[]`, and use unique reviewer-facing read names in public evidence without a v1 compatibility output.

- Replace `signal.analysis/v4` with compact `signal.analysis/v5`: retain input/reference/configuration identities, call count and trim, merged noisy regions, alignment summary, normalized variants with concise call mappings, and warning counts; remove filenames, full sequences, rolling windows, gapped rows, method constants, full peaks, vendor data, and redundant fields without a compatibility output.
- Replace `signal.analysis/v3` with `signal.analysis/v4`, adding bounded rolling signal-quality windows, merged candidate-noisy regions, and a signal-processing method identity without a v3 compatibility path.
- Replace strict configuration schema version 3 with version 4, requiring the minimum two-window noisy-interval setting.
- Replace `signal.analysis/v1` with compact `signal.analysis/v3`: omit bulk records; use concise coordinate names and direct mapped variant `calls` with A/C/G/T peaks plus relative/vendor quality.
- Remove `--out-prefix`; analyses now publish as `results/<trace-stem>.json` and create the results directory when needed.
- Replace strict configuration schema version 1 with version 2, requiring variant peak, relative-quality, and inclusive-region settings.

### Added

- ADR-0055 promotes the completed poly-C research into a read-local production architecture boundary: future phase evidence is downstream of selected alignment, initially limited to verified rCRS HV1/HV2 contexts, keeps not-applicable/insufficient/measured availability distinct from interpretation, and cannot change variants or unit-mass sample contribution without a separate validated policy. No detector, `PhaseState`, threshold, weight, config key, or public schema is introduced.

- Recurrent-locus phase research now publishes `signal.validation_phase_recurrent_loci/v1`, hash-binding the source poly-C phase and phase-hypothesis artifacts and reconstructing exact profile-bearing window membership for rCRS 253/297/302/16194/16197 before emitting complete candidate curves plus per-locus candidate contributions. Missing-profile loci remain explicit with zero containing windows; no interval approximation, winning offset, score, threshold, truth label, or production behavior is introduced.

- Post-poly-C phase explainability research now publishes `signal.validation_phase_explainability/v1` with threshold-free candidate-envelope summaries at window and read levels. The artifact exposes shifted-reference/residual extrema, ranges, and maximum non-zero-mass explainability without emitting a winning offset, review label, threshold, or production behavior.

- Post-poly-C parameter-sensitivity research now publishes `signal.validation_phase_sensitivity/v1`, evaluating a full-factorial window-size/stride/max-offset grid through the authoritative phase-hypothesis engine and characterization aggregation while retaining every candidate independently and selecting no preferred parameter set or threshold.

- Poly-C opposite-orientation research now publishes `signal.validation_polyc_orientation_controls/v2` directly from the completed validation corpus, retaining every eligible same-case/same-locus post-tract read and opposite selected-orientation pre-tract control without pair selection or Cartesian expansion. The artifact preserves PCR/run/amplicon provenance and descriptive role profile geometry, including mean-profile Total Variation, without thresholds or production interpretation.

- Post-poly-C phase characterization now publishes hash-bound `signal.validation_phase_characterization/v1` adjacent-window persistence, exact-distance trajectory, and observed-interrupt strata over the complete candidate curves from `signal.validation_phase_hypotheses/v1`. The research preserves every offset independently and defines no best shift, classifier, recovery threshold, genotype, length-heteroplasmy call, or production behavior.

- Tracy-inspired post-poly-C phase research now publishes hash-bound `signal.validation_phase_hypotheses/v1` sliding-window candidate curves over integer reference offsets in sequencing order. Each candidate preserves informative-position count plus mean zero-phase, shifted-reference, and unexplained residual profile mass, allowing structured dephasing to be studied separately from unstructured signal degradation without selecting a winning shift or changing production calling.

- Local poly-C phase-instability research now publishes hash-bound `signal.validation_polyc_phase/v1` observations and descriptive summaries for reads that actually span validated rCRS HV2/HV1 C tracts, preserving sequencing-direction path region, genomic/call-order distance, profile impurity, previous/current/next reference-base mass, and read-local T310/T16189 evidence without defining a phase score, recovery cutoff, genotype, artifact verdict, or production confidence change.

- Reviewer-facing sample differential loci now preserve the concise Tracy-derived signal shape needed for evidence-aware review: factorized read/state/profile topology plus each call-backed observation's normalized reference-oriented A/C/G/T `EvidenceProfile` and existing candidate-noisy context, while corrected amplitudes/SNR and consensus interpretation remain internal.

- ADR-0052 records the directional confidence invariant for unstable mtDNA poly-C tracts: evidence after an unstable tract in sequencing order must be treated as lower-confidence than otherwise equivalent evidence that has not crossed the tract. Detection, recovery modeling, thresholds, and production behavior remain deferred for validation.

- Local validation curation now prepares a hash-bound `signal.validation_curation_queue/v1` from completed audit artifacts: one immutable queue containing every mixed locus and flagged read, plus a separate blank decisions template for human review. The queue records recurrence and existing audit context without assigning truth, exclusions, holdout membership, threshold-fit inclusion, or production behavior.

- Local validation audit now publishes hash-bound `signal.validation_audit/v1` read/locus/case review strata from completed corpus, research tables, and SHA-bound validation-log metrics. Corpus-relative low-identity/high-noise/aggressive-trim/short-coverage flags require sufficiently populated amplicon-direction strata; mixed loci retain retained-read edge/orientation context. Audit flags remain observational and do not alter truth, holdout assignment, eligibility, or production thresholds.

- Local validation research now streams completed corpora into hash-bound `signal.validation_research/v1` datasets with joined locus/observation CSV tables and exact descriptive nearest-rank profile-geometry percentiles, while deliberately performing no threshold selection or holdout tuning.

- Local validation research now has manifest-driven corpus orchestration that SHA-256 binds each trace to exactly one validation case, enforces source-group holdout consistency, preserves truth/grouping metadata outside the Rust core, validates `signal.validation_locus/v2` provenance, and stages all selected cases before no-overwrite publication under ignored `validation-results/`.

- Local `signal-validation` research tooling now exports deterministic all-covered per-locus `signal.validation_locus/v2` JSONL under ignored `validation-results/`; v2 replaces research-only v1 and adds strict per-read call/PLOC/primary-peak/signal-event diagnostics with reference-oriented channel evidence so unexplained basecall/profile disagreement can be investigated before threshold fitting.
- Validation event-placement research now explicitly compares primary basecall event selection with total-corrected-signal event refinement without changing either scientific rule or introducing artifact/heteroplasmy verdicts.
- Validation research now specifies corpus strata, truth/provenance hierarchy, grouped anti-leakage development/holdout design, LoB/LoD-style threshold research, point-mixture versus length-mixture separation, and explicit promotion gates before any profile-geometry threshold can enter production.
- Internal eligible-profile evidence now retains threshold-free within-read impurity, between-read dispersion, total heterogeneity, and forward/reverse Total Variation geometry, preserving the distinction between reproducible mixed chromatogram evidence and disagreement across otherwise clean reads without adding thresholds or biological verdicts.
- Sample aggregation operational metrics now live in a dedicated pipeline module instead of the sample orchestration path, including production consumption of profile-geometry summaries.
- Internal differential loci now derive arithmetic mean A/C/G/T evidence profiles for non-empty total/forward/reverse unit-mass support partitions, preserving contributor counts and avoiding any winning-base, agreement, or confidence interpretation.
- Internal differential loci now retain unweighted eligible-profile A/C/G/T support with total and forward/reverse partitions, using unit read mass only and production logging of contributor topology/profile mass without exposing nucleotide composition or selecting a consensus.
- Internal differential-locus observations now carry structural nucleotide-contribution eligibility after profile availability: profile-bearing calls are eligible even when unresolved or in candidate-noisy context, missing-profile calls are excluded from nucleotide aggregation, and deletions remain separate events; production logging consumes all three states without adding consensus weights.
- Internal differential-locus support topology now records the number of observations with an available basecall-independent `EvidenceProfile` plus forward/reverse profile availability, establishing a pre-consensus nucleotide-profile denominator without voting or weighting.
- Internal sample reconciliation now retains one unified reference-oriented `CallSignalEvidence` per source call, carrying corrected A/C/G/T amplitudes, per-channel SNR, optional `EvidenceProfile`, and existing noisy-region membership; obsolete split profile/noise lookup paths are removed, production logs consume quantitative channel summaries, and `signal.sample_evidence/v7` remains unchanged.
- Internal call-backed sample evidence now preserves existing merged candidate-noisy-region membership for differential-locus observations and normalized-variant calls, with deletion context left absent and production aggregate logging, without changing `signal.sample_evidence/v7` or eligibility semantics.
- Internal differential-locus evidence now retains factorized total/read-orientation/reference-alternate-unresolved-deletion support topology with production logging, without changing `signal.sample_evidence/v7` or introducing a consensus vote.
- Internal sample reconciliation now preserves basecall-independent A/C/G/T `EvidenceProfile` values for call-backed differential-locus and normalized-variant evidence, projected to reference orientation without public schema changes or missing-profile fallback.
- Factorized sample-variant support topology summarizing observed/eligible and forward/reverse read counts while preserving every authoritative per-read support record and avoiding confidence or independence claims.
- Pre-consensus sample coverage topology derived from selected post-trim reference segments, exposing compact local read depth and forward/reverse orientation depth without majority voting or read rejection.
- Tracy-derived trace-integrity evidence: valid PLOC-defined processing now preserves optional PBAS/PCON length mismatches as warnings instead of rejecting the file, records PLOC spacing and exact signed-16-bit clipping, and exposes an unthresholded maximum-to-median corrected event-signal ratio for artifact-resilience validation.
- Tracy-derived pre-consensus sample overlap admission: every independently placed read pair with shared reference coverage records canonical-base overlap/agreement, deterministic eligibility, and exact exclusion reasons without pair-first merging or gap-quality synthesis.
- Required Rust source-policy CI gate rejects deprecated compatibility APIs, legacy/backward-compatibility feature/declaration scaffolding, and diagnostic suppressions that could hide dead/unused/deprecated production code.
- Fixed-point profile-aware semi-global Gotoh placement (`signal.profile_gotoh/v1`) using post-trim basecall-independent A/C/G/T evidence profiles, explicit 1024-unit quantization, reverse profile complementation, and score-only orientation ties without changing public JSON schemas.
- Internal basecall-independent `LocusEvidence` and normalized `EvidenceProfile` derived directly from analyzed A/C/G/T channel signal at deterministic refined PLOC events; zero-signal loci have no synthetic fallback profile and public JSON contracts are unchanged.
- Multi-read `signal sample` evidence now preserves filtered normalized-variant observations, reviewer-facing read provenance, reference-oriented four-channel peak/quality evidence, and focused reference-support quality at differential loci while omitting routine all-reference loci.

- Reference-free `signal basecall <trace.ab1>` with one atomic no-overwrite `signal.basecalls/v1` JSON result containing full primary/ambiguity/retained sequences, trim bounds, merged noisy regions, provenance, and warning counts through the same validated read-processing stages as reference analysis.
- Deterministic `signal.windowed_snr/v1` analysis with local median/first-difference-MAD estimates, finite SNR features, and merged call/sample candidate-noisy regions requiring at least two candidate windows by default.
- Complete one-AB1 Rust analysis pipeline with strict TOML configuration and typed errors.
- Bounds-checked canonical ABIF decode, single-record FASTA identity, and internal four-channel signal evidence.
- Signal-derived re-calling at PLOC loci, relative quality scoring, and end-only trimming.
- Bounded deterministic forward/reverse semi-global Gotoh with circular-reference support.
- Normalized primary-sequence SNV and small-indel extraction with original-call evidence.
- Versioned compact `signal.analysis/v3` schema, synthetic example, exact SNV/indel call-to-PLOC mapping tests, atomic no-overwrite publication, and end-to-end tests.
- Exact one-to-one Rust source manuals, normative pipeline documentation, biological limitations, and Apollo deviation records.
- Shared SHA-256 identity helper in `src/checksum.rs`, used by config, trace, and reference loading.
- Locked uv environment and typed schema validator for reproducible JSON contract checks in development and CI.
- External `scripts/analyze_samples.py` wrapper for safe per-sample local-corpus orchestration without changing the one-file CLI.
- Rust-native append-only per-operation logging under `logs/`, with standalone trace logs, sample-scoped logs containing nested trace-stage records, `SIGNAL_LOG_DIR` isolation, and run-correlated single-line records.

### Changed

- Canonical mtDNA alignment now score-verifies and right-shifts repeat-equivalent maximum-score indel placements to one 3'/right-most rCRS-light-strand topology before placement deduplication; variant representation preserves that canonical gap anchor instead of applying a second left/circular positional normalization. Genuine non-equivalent score ties remain errors, and circular canonicalization cannot rotate across the rCRS origin seam.
- Reference-guided alignment substitution scores now derive from `EvidenceProfile`; affine gap, traceback, circular topology, public primary-sequence callable/identity metrics, and downstream primary-sequence variant extraction remain unchanged. Internal/logged alignment scores are fixed-point units rather than raw configured score totals.
- PLOC neighboring-midpoint window geometry is shared between basecalling and signal evidence instead of being owned only by the caller; obsolete basecall-dependent `CallSignalMetrics`/`PrimaryEventSignalMetrics` are removed.
- Candidate-noisy signal annotations are observation-only and do not affect calls, trim bounds, alignments, warning totals, or variant eligibility.
- MVP output is one compact `results/<trace-stem>.json`; the earlier JSON-plus-VCF plan is superseded.
- Quality is explicitly uncalibrated relative score; vendor PCON remains separate.
- rCRS topology is circular and origin-spanning alignments/indels have explicit canonical coordinates.
- Basecalling is `signal.peak_recall/v3`: qualifying channels must pass the configured ratio at both their selected peak and the uniquely strongest primary peak sample, rejecting remote secondary maxima while preserving primary selection, tie handling, PLOC fallback, and one/two/three/four-channel call semantics.
- Variant calling is `signal.primary_difference/v4`: normalized anchors must lie in configured inclusive regions; SNV and every inserted-base supporting call must meet the configured peak/quality gates; additionally, SNVs with more than one co-localized qualifying channel remain observed but are ineligible for clean reporting with `mixed_supporting_signal`. Insertions/deletions are not subjected to this point-mixed-signal rule.
- Alignment scores are 64-bit (`i64`) while configuration score deltas remain 32-bit (`i32`).
- Origin crossing is represented once by `alignment.wraps_origin`; Rust still counts it in the operational warning summary without duplicating it in JSON.
- `P2BA.1` is ignored; only optional `PBAS.2` and `PCON.2` vendor evidence is consumed.
- Relative quality scores manually clamp the score fraction to `[0, 1]` so results stay in `[0, max_relative_quality_score]`.
- Operational logs now record concise aggregate metrics and timings for every processing stage, exact warning categories, stage-aware failures, and each removed variant's kind/position/reasons without alleles or raw scientific payloads.
- The bundled `variant_calling.minimum_peak_height` is raised from 100 to 150.
- The external batch runner now preflights and builds before destructive cleanup, removes only selected sample result directories and selected sample logs, rejects ambiguous identities and symlinked cleanup targets, preserves unselected artifacts, writes helper trace-operation logs only to temporary workspaces, and persists one nested trace-aware sample log per sample. A later analysis failure may leave partial new outputs.
- Rename the stale documentation names to `docs/delivery-record.md` and `docs/requirements.md`.

### Fixed

- Poly-C validation research now derives before/after state from actual call order across the complete tract and computes reference distances/neighbors on circular rCRS, so origin-wrapping reads remain on the correct post-tract path; outside-tract observations without call indexes remain explicitly unresolved instead of falling back to linear coordinates.

- Accept ABIF directory entries whose declared allocation is larger than the logical element payload, including real-world oversized `tdir.1` root-directory allocations, while still bounds-checking the full allocation and rejecting undersized/truncated payloads.

- Anchor `LocusEvidence`/`EvidenceProfile` to the positive total-corrected-signal local event nearest PLOC, with deterministic equal-distance tie handling and PLOC fallback, preventing a stronger neighboring chromatogram event elsewhere in the midpoint window from stealing a locus profile while preserving nucleotide/basecall-independent profile composition.
- Reject batch cleanup roots that overlap inputs or each other, preventing selected cleanup from deleting protected data.
- Synchronize batch result directories and newly created parent entries after atomic publication, rolling back a new destination when durability cannot be confirmed.
- Preserve every selected channel peak's internal sample position while keeping it omitted from compact v5.
- Accept uppercase IUPAC vendor base evidence and both one-byte ABIF PCON element representations without changing signal-derived calls.
- Avoid stale PID-only temporary-output name collisions and remove a just-published target when final synchronization fails.
- Select the best span-valid circular traceback when a higher-scoring unbounded candidate exists in the doubled reference.
- Canonicalize origin-spanning repeat indels independently of their observed anchor while preserving observed call mappings.
- Derive indel anchors from the actual adjacent reference coordinate at alignment boundaries and reject any emitted reference allele that disagrees with the supplied reference.
- Prevent four-channel unresolved loci from contributing a guessed primary base and use 64-bit alignment scores without saturation.

### Removed

- Removed the temporary `software_version` field from analysis and reference-free basecall provenance; software/build provenance is deferred until a stable versioning strategy is defined.
- Not-implemented scaffold behavior and all planned VCF/BCF compatibility paths.
- Misleading fully de novo terminology, hardcoded poly-C/HV behavior, and genotype/heteroplasmy claims from MVP scope.
- `src/reference/checksum.rs`; SHA-256 is consolidated into the shared `src/checksum.rs`.
