# `src/pipeline/analyze.rs`

## Purpose

Sequences one complete AB1-to-compact-v5 analysis and owns operational stage
logging plus result publication.

## Responsibilities

- Open the per-trace Rust logger and emit ordered, run-correlated aggregate
  summaries and timings for input loading, basecalling, signal processing,
  quality control, alignment, variant calling, and publication readiness.
- Run the pure scientific stages in order and pass every completed internal model
  to `report::build`.
- Log signal-processing window/region counts and the maximum secondary SNR across
  internal windows; that aggregate is operational and not part of v5 JSON.
- Emit one WARN record for each removed variant with kind, contig, position, and
  reasons but no alleles, followed by the final warning-category summary.
- Assemble and serialize `signal.analysis/v5`, synchronize the mandatory
  pre-publication record, and atomically publish `results/<trace-stem>.json`.
- Preserve the original analysis error, combining it with a terminal logging
  failure as `Error::AnalysisAndLog`.

## Non-responsibilities

No binary parsing, peak selection, signal feature formulas, trimming calculations,
alignment scoring/traceback, variant normalization, or JSON field definitions.

## Key types and functions

- `run(args) -> Result<()>`: validates the trace stem, opens logging, tracks total
  elapsed time/current stage, and applies combined analysis/logging error policy.
- `run_logged(args, logger, stage, analysis_started) -> Result<()>`: sequences the
  complete stage flow and output transaction.

## Invariants and errors

- Scientific stage functions remain side-effect-free; pipeline orchestration owns
  operational logging and publication.
- The pipeline succeeds only after atomic JSON publication and never overwrites an
  existing result.
- `result_ready_for_publication` is synchronized before publication and does not
  claim the output is already committed; no mandatory post-publication log exists.
- Logs omit sequence strings, alleles, configured region contents, individual
  peaks/calls, detailed alignment rows, and JSON bodies.
- The pipeline computes its operational warning total from the three public JSON
  categories plus vendor-disagreement and origin-wrap events before moving stage
  results into report assembly. Operational-only categories never enter the JSON
  model.
- Stage failures propagate unchanged when the ERROR record synchronizes; if that
  logging also fails, `Error::AnalysisAndLog` retains both errors.

## Dependencies

- `input`, `logger`, `basecalling`, `signal_processing`, `quality_control`,
  `alignment`, `variant_calling`, and `report`.
- `cli::AnalyzeArgs`, `error::{Error, Result}`, `PeakSource`, and `VariantKind`.

## Biological semantics

The stage order is decode/load, signal-derived re-calling, observation-only rolling
SNR analysis, relative quality scoring/end trimming, bidirectional alignment, and
normalized configured variant calling. Compact v5 then exposes provenance, read
bounds, merged noisy regions, a selected-alignment summary, variants with concise
supporting evidence, and public warning counts rather than raw intermediate data.

## Tests

End-to-end tests cover ordered stage events, signal-window/region logging, compact
v5 output, removed-variant reasons, warning levels, payload omissions, and
stage-aware failures.

## Status

Implemented.
