# Signal Roadmap

## Implemented MVP

- strict one-file analyze/basecall CLI, TOML configuration, typed errors, and resource caps;
- bounds-checked canonical ABIF decode, reference-free basecalls-v1 output, and one-record FASTA loading for analysis;
- signal-derived PLOC re-calling with explicit ambiguity evidence;
- observation-only rolling SNR windows and merged candidate-noisy regions;
- uncalibrated relative quality and end-only trimming;
- bounded forward/reverse semi-global Gotoh with circular topology;
- primary-sequence SNV and ≤50 bp indel extraction/normalization;
- compact `signal.analysis/v5` JSON with provenance, read/trim, merged noisy-region, alignment, normalized-variant, and warning summaries plus atomic core-CLI no-overwrite publication;
- clean external batch reruns with full preflight, selected-only destructive cleanup, ambiguity/collision/symlink rejection, and unselected-artifact preservation;
- synthetic unit/integration tests, source/manual mirror, schemas, and CI gates.

## Release evidence still required

An approved, non-identifying or redistributable real AB1 must exercise the complete rCRS path with documented checksum, expected orientation/region, effective config, normalized differences, runtime, and memory. This is validation evidence, not missing product code.

## Post-MVP candidates

1. approved real-trace regression corpus;
2. validated baseline correction/smoothing and noise-aware calling or variant policy;
3. empirically calibrated quality/confidence model;
4. mixed-base and two-allele decomposition with validated heteroplasmy limits;
5. additional reference topologies/formats and compressed FASTA;
6. indexed search for longer/multi-contig references;
7. SCF input;
8. parallel or resumable batch orchestration beyond the current clean sequential wrapper;
9. optional derived interchange formats only under a separate versioned contract.

Each candidate requires requirements/ADR/schema changes, mirrored source docs, focused tests, and biological validation.

## ML-ready JSON direction

A future machine-learning path should preserve the compact production contracts while making the internal evidence available through an explicit training contract. The recommended boundary is an opt-in offline exporter that creates one independently versioned training example, such as `signal.training-example/v1`, rather than adding unstable bulk fields to `signal.analysis/v5` or `signal.basecalls/v1`.

This is a direction record, not an implementation commitment. No `features` module, training schema, CLI command, or training output exists or should be created until the delivery phases below approve a task, corpus, feature registry, label registry, and closed schema. See [ADR-0016](adr/0016-defer-ml-feature-boundary.md) for the formal decision.

A training exporter conflicts with the current one-file CLI contract: `SRS-IN-001`, `SRS-IN-010`, and `SRS-OUT-001` fix each command to one input and exactly one command-specific JSON output with no duplicate compatibility output. An opt-in exporter therefore requires an approved ADR and SRS update establishing its invocation contract (separate subcommand, output path, overwrite semantics) before any `report::training` or pipeline integration.

Conceptually, one training example contains:

```text
{
  schema_version,
  provenance,
  feature_set
}
```

The example embeds a minimal, privacy-reviewed provenance and scientific projection, not the unchanged full command result. The basecall result contains complete identifying sequences; blindly embedding it would contradict [`data.md`](data.md). The training contract must therefore carry only the identities and evidence each approved prediction target needs, with explicit retention and redaction rules. `feature_set` identifies one reviewed feature definition and contains ordered feature records. Labels are independently governed data joined through an opaque example identity; an example may remain unlabeled. A dataset materialization step may combine approved labels with exported examples, but current calls, quality scores, noisy-window flags, alignments, and variants are pipeline predictions or observations, not ground truth.

Feature extraction observes the same immutable completed scientific state after all required stages finish and before report-bundle ownership movement or file publication. It must not depend on report-layer projection types or recompute scientific calculations.

### First task and inference boundary

Start with base-call correctness and empirical quality calibration. They have clear per-call units and can use the shared reference-free stages. Mixed-base decomposition, heteroplasmy estimation, and variant classification should remain later tasks because they need different truth, study design, and biological claims.

Before implementing an exporter, define for each model:

- prediction target and unit of observation;
- inference-time stage and permitted inputs;
- independent truth source and adjudication process;
- training, calibration, and held-out evaluation metrics;
- intended behavior when a feature or label is unavailable.

Every feature must be classified by availability: `pre_call`, `post_call`, `post_qc`, or `post_alignment`. A reference-free caller cannot use alignment- or variant-derived features. A model also must not use a threshold decision or exclusion reason to predict that same decision.

### Potential ML uses

ML should first add calibrated observations and review assistance around the deterministic pipeline. It should alter scientific results only after task-specific evidence shows an improvement over transparent baselines.

| Horizon | Use case | Model output | Required independent truth and evaluation |
|---|---|---|---|
| Near term | Per-call confidence calibration | Probability that each primary call is incorrect, plus calibration uncertainty | Consensus or orthogonal truth bases; compare log loss, Brier score, calibration error, and error detection at fixed retained yield against the current relative score. |
| Near term | Read triage and resequencing recommendation | `pass`, `manual_review`, or `resequence` score with reason categories | Replicate success and blinded review outcomes; measure false-pass rate, review workload, and useful-read retention across runs and instruments. |
| Near term | Artifact and noisy-region classification | Call/window probabilities for low signal, baseline drift, impulse, saturation, compressed spacing, pull-up, or mixed signal | Approved expert annotations and controlled synthetic perturbations; report per-class precision/recall and performance on unseen acquisition runs. |
| Near term | Out-of-distribution and run-drift detection | Distance or anomaly score for a trace/run relative to the validated training domain | Approved run/instrument metadata and known-good control distributions; evaluate detection of held-out instruments, chemistries, and deliberately shifted synthetic traces. |
| Medium term | Trim-boundary recommendation | Suggested retained interval and confidence | Truth-aligned call correctness or independently curated usable boundaries; compare correct retained bases and residual error at equal yield. Keep end-only deterministic trimming as the fallback. |
| Medium term | Base-call correction | Per-call A/C/G/T/N probabilities and an optional corrected base | Independent truth sequences with donor/run-grouped splits; measure total error, substitutions/indels, ambiguity handling, and regressions on already-correct high-quality calls. Run in shadow mode before any replacement. |
| Medium term | Variant-candidate review prioritization | Probability that a pre-filter SNV/indel candidate is real and a review-priority score | Orthogonally established variant truth including representative negative candidates; measure sensitivity, precision, calibration, and performance by variant kind and signal regime. Do not train only on reported v5 variants. |
| Research | Learned baseline correction or denoising | A separate processed waveform or correction parameters | Paired clean/noisy evidence, replicates, or controlled synthetic corruption; verify base/variant accuracy and preservation of genuine secondary peaks. Never overwrite decoded channels. |
| Research | Mixed-template decomposition | Major/minor bases, mixture fraction, uncertainty, and an explicit unsupported state | Controlled mixtures with known component sequences and fractions, then independent real mixtures; establish false-positive rate and limit of detection before making heteroplasmy claims. |
| Research | End-to-end neural basecalling | Sequence or per-locus base distribution from bounded channel context | Large diverse truth-aligned corpus; compare against engineered-feature models, test domain transfer, preserve coordinate mapping, and retain an auditable deterministic fallback. |

Active learning can support every horizon by ranking uncertain or novel traces for annotation. Selection must be recorded so the labeled corpus does not masquerade as an unbiased prevalence sample, and final evaluation data must never enter the annotation-selection loop.

Recommended delivery order is: call-confidence calibration, review/resequence triage, artifact and out-of-distribution detection, trim recommendation, base correction, and only then reference-aware or mixed-template models. The first four can remain observation-only and provide dataset feedback without changing biological calls.

ML is not appropriate for bounds-checked ABIF parsing, checksum identity, coordinate conversion, deterministic indel normalization, schema validation, or atomic publication. Those are exact engineering rules and should remain conventional typed code.

### Initial engineered feature set

The first feature set should reuse bounded evidence already retained by the typed pipeline and add only deterministic, documented projections.

| Granularity | Candidate features | Important limits |
|---|---|---|
| Read | sample/call counts, trim fraction, unresolved and ambiguous-call rates, call-spacing summaries, peak-ratio summaries, and SNR summaries | Summary values must document denominator, units, rounding, and empty-data behavior. |
| Call | original index, PLOC and call-window bounds, neighboring spacing, canonical A/C/G/T peak heights and offsets, peak-source flags, qualifying-channel mask/count, strongest-to-secondary ratios, QC penalty, relative quality, and retained status | Channel order is always A/C/G/T. Relative quality is normalized within a read and is not a calibrated local probability. |
| Rolling window | ordered call/sample intervals, minimum primary SNR, maximum secondary SNR, and observational candidate-noisy status | The existing six-decimal calculation is uncalibrated; the threshold-derived status is not a truth label. |
| Reference-aware candidate | pre-filter call mappings, local alignment context, candidate kind, and eligibility inputs | Only valid for tasks that have reference/alignment access. Export positive and negative candidates before configured filtering to avoid selection bias. |

Compact analysis v5 contains detailed evidence only for calls supporting reported variants, so v5 files alone cannot provide representative negative examples. Vendor PBAS/PCON evidence should remain outside the initial portable feature set unless a defined task, license/data policy, and independent evaluation justify it.

Full channel arrays should also be deferred. If engineered features prove insufficient, a later feature-set major version may add fixed-width per-call waveform snippets with explicit normalization, padding, and masks. Large signal tensors should live in a referenced compressed columnar or tensor artifact rather than be repeated as JSON arrays; decoded channel evidence must never be overwritten.

### Feature module boundaries

The existing scientific workflow should remain unchanged. One explicit `features` subsystem sits after raw-data processing and all command-specific scientific stages, immediately before assembly of the independently versioned training JSON. Extraction, engineering, and serialization are different responsibilities and must not be combined in pipeline or report code.

```text
AB1 + configuration
        |
        v
existing shared workflow
  decode -> basecalling -> signal processing -> quality control
        |
        +------------------------------- basecall complete
        |
        +-> reference -> alignment -> variant calling
                                         |
                                         +-- analysis complete
                                                     |
                                                     v
                                              features::extract
                                                     |
                                                     v
                                             ExtractedEvidence
                                                     |
                                                     v
                                              features::engineer
                                                     |
                                                     v
                                                  FeatureSet
                                                     |
                                                     v
                                               report::training
                                                     |
                                                     v
                                  signal.training-example/v1 JSON
                                    { provenance + final features }
```

The feature subsystem is therefore a post-pipeline projection boundary, not a new scientific stage. Basecalling, signal processing, quality control, alignment, and variant calling neither call it nor consume its output. They continue to produce the same typed results and remain independently testable.

A provisional future source layout is:

```text
src/
├── features/
│   ├── mod.rs          # post-pipeline facade and extraction/engineering sequence
│   ├── evidence.rs     # private ExtractedEvidence (transient, not a model type)
│   ├── feature_set.rs  # canonical serializable FeatureSet
│   ├── extract.rs      # copy or derive local evidence from validated models
│   └── engineer.rs     # deterministic ratios, offsets, summaries, and masks
└── report/
    └── training.rs     # JSON projection only; no feature calculations
```

This layout is provisional and must be finalized by the Phase-2 ADR. The module name `features` collides conceptually with the existing `signal_processing::features` submodule (rolling-SNR calculation); the ADR must resolve the naming (candidates: `feature_export`, `training_features`, `ml_features`). `ExtractedEvidence` and `FeatureSet` are feature-subsystem types owned by `src/features/`, not `src/model/` — `model/` is the shared scientific domain vocabulary and serializable production result records, not transient post-pipeline algorithmic state. A feature registry and cross-field validator module are deferred until at least two feature definitions exist; Phase 1-2 uses strongly-typed Rust structs and a closed JSON schema.

If implemented, every new Rust source must receive its exact `docs/src` manual counterpart and focused tests under the matching relative layout, and all new code must land in one atomic commit so the docs-mirror and clippy dead-code gates stay green.

#### Extraction boundary

`features::extract` receives the complete immutable output bundle for one successful command. For `basecall`, that bundle contains the decoded trace, calls, signal analysis, and QC result. For `analyze`, it additionally contains the reference, selected alignment, and pre-filter/final variant evidence. Extraction may select values or make local coordinate-preserving derivations such as neighboring PLOC spacing, peak offsets from PLOC, retention membership, and alignment-to-call mappings. It must not:

- parse ABIF, configuration, FASTA, JSON, or dataset manifests;
- mutate decoded channels or scientific stage results;
- apply dataset-fitted normalization, imputation, or learned parameters;
- assign truth labels or infer model predictions;
- perform filesystem I/O or serialization.

Extraction returns a private `ExtractedEvidence` value ordered by original call/window/candidate coordinates. This type is internal to the features module, not a `model/` record. Reference-free and reference-aware extraction must be explicit entry points so alignment features cannot accidentally enter a reference-free model.

#### Engineering boundary

`features::engineer` consumes only `ExtractedEvidence` plus a versioned feature definition. It computes deterministic model inputs such as peak ratios, one-hot or bit masks, bounded offsets, aggregate rates, and quantiles. It must preserve source indexes needed to join call/window/candidate features back to evidence.

No training-library preprocessing should silently create additional production features. Dataset-fitted transforms such as scaling, clipping learned from data, imputation, or vocabulary fitting belong to a separately versioned dataset/model pipeline. Their fitted parameters and training-split identity must be recorded. If a transform is required at inference, its output must either be included in a later `FeatureSet` version or be reproducibly defined by the model artifact.

#### Canonical feature model and JSON boundary

`FeatureSet` is the single canonical representation of model-ready engineered features. The training reporter serializes it without recomputing, renaming, flattening, filtering, or defaulting fields. Every feature that a supported model can consume must therefore appear exactly once in the versioned training JSON with the same value and semantics; there must be no hidden sidecar feature or report-only calculation.

Intermediate extraction evidence does not have to be duplicated when it is not a model input. Evidence that is itself a final feature, such as a channel peak height or call spacing, appears in `FeatureSet`. Large future waveform tensors may remain referenced artifacts, but their identity, shape, dtype, ordering, normalization, masks, and checksum must be present in JSON.

The feature JSON should retain its natural granularity rather than flattening calls and windows into ambiguous global keys:

```text
feature_set: {
  name,
  version,
  definition_sha256,
  read: { ... },
  calls: [ { index, ...final_call_features } ],
  windows: [ { calls, samples, ...final_window_features } ],
  candidates: [ { id, ...final_candidate_features } ]
}
```

`calls`, `windows`, or `candidates` may be absent only when the selected feature-set schema explicitly excludes that granularity. Labels remain outside `FeatureSet`, and the compact production result remains unchanged.

#### Dependency and ownership rules

Dependencies point from `features` toward `model` and configuration-owned method definitions. Scientific algorithms must not depend on report types, JSON field names, labels, dataset tooling, or model runtimes. `report::training` depends on the canonical `FeatureSet`, while current production reporters continue to depend only on completed scientific models.

The pipeline may orchestrate feature export after scientific stages complete, but it must not calculate individual features. This keeps three separately testable contracts:

1. domain models to extracted evidence;
2. extracted evidence to canonical final features;
3. canonical features to byte-deterministic JSON.

### Feature, schema, and provenance rules

A feature registry must define every field's stable name, type, units, coordinate and strand convention, ordering, null semantics, computation method/version, inference availability, and leakage classification. Leakage classification must be target-relative, not a static field property: a QC penalty or exclusion reason may be a valid input for one prediction target and leakage for another. Each feature's leakage tag must name the prediction target and inference point it applies to. Analysis-result, configuration, feature-set, and label schemas have independent version domains.

The training example contract should require:

- a closed Draft 2020-12 JSON Schema and a new major version for semantic or structural breaks;
- deterministic array ordering, A/C/G/T channel order, tie-breaking, and serialization;
- finite values with defined precision, rejecting NaN and infinity;
- existing input, configuration, and optional reference identities;
- immutable extractor/build identity, feature-set version and definition hash, and explicit transform parameters;
- enough retained configuration and method provenance to reproduce features rather than relying on an unavailable checksum target.

### Labels, splits, and data governance

Approved labels must come from an independent consensus, orthogonal assay, or documented expert adjudication. Label records need their own schema version, source/release identity, annotation method, confidence, and reviewer or adjudication provenance. Current `primary`, `ambiguity`, `relative_quality`, `candidate_noisy`, reported/excluded status, and exclusion reasons may be features or pseudo-labels for exploration, but they must never be presented as independent truth.

Dataset construction must:

- group splits by donor/sample and acquisition run rather than randomly splitting calls or windows;
- deduplicate source identities and keep all related traces in one split;
- fit normalization, imputation, and feature selection on training folds only;
- reserve an untouched approved test set and report class balance, missingness, and domain composition;
- treat AB1 hashes, sequences, biological differences, labels, and dense signal features as identifying data under [`data.md`](data.md).

The current filename-free provenance is insufficient to establish donor/run grouping, so approved dataset manifests must provide opaque group identities without placing identifying names in exported examples.

### Delivery phases and gates

1. **Task and corpus:** choose the first prediction target, acquire approved truth-labeled traces, define metrics, and record privacy/retention rules.
2. **Contract design:** approve an ADR, feature registry, label registry, closed schema, synthetic example, coordinate rules, and size bounds. Keep current production results unchanged. No Rust source, schema file, or CLI modification may be created before this phase and Phase 1 are approved.
3. **Deterministic export:** implement a pure offline projection from completed typed models, with no changes to calling, trimming, alignment, filtering, or current publication behavior. All new Rust sources, their `docs/src` mirrors, CLI wiring, and tests must land in one atomic commit so the docs-mirror and clippy dead-code gates stay green.
4. **Dataset validation:** add schema validation, byte-determinism checks, golden feature vectors, cross-field invariants, missingness/distribution checks, source deduplication, and grouped split tests. Audit upstream survivorship: exporting only successfully completed runs biases the corpus, so dataset validation must record basecall failures, alignment drops, and filter removals that excluded traces from the export.
5. **Baseline training:** compare transparent baselines, report held-out discrimination and calibration, analyze errors by run/read region/signal quality, and document feature ablations.
6. **Shadow evaluation:** run a selected model as observation-only output on new approved data and monitor drift. Do not let it alter scientific results.
7. **Behavioral adoption:** only a later ADR, requirements/config/result version, focused tests, and biological validation may allow a model to change calls, quality, trimming, or variants. Preserve a deterministic non-ML evidence path for audit.

Initial success is a reproducible, privacy-reviewed dataset contract and trustworthy held-out evaluation, not deployment of a model or a claim of Phred calibration, heteroplasmy sensitivity, or clinical performance.
