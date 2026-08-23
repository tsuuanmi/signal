# `src/pipeline/analyze.rs`

## Purpose

Sequences the complete end-to-end scientific stages for one AB1-to-JSON
analysis.

## Responsibilities

- Open the per-trace Rust logger and record ordered, run-correlated aggregate
  summaries and timings for every stage boundary.
- Emit WARN records for exact final warning categories and each removed variant's
  kind, contig, position, and rejection reasons without alleles.
- Record terminal failures with the active stage while omitting raw scientific
  payloads.
- Load inputs, then run basecalling, observation-only signal processing, quality
  control, alignment, and configured variant calling in order.
- Assemble the compact `signal.analysis/v4` document, serialize it, and publish it
  atomically to `results/<trace-stem>.json` without overwriting an existing target.

## Non-responsibilities

No binary parsing, scoring loops, variant normalization, or serialization format
logic.

## Key types and functions

- `run(args) -> Result<()>`: opens logging and preserves the original stage error.
- `run_logged(args, logger, stage, analysis_started) -> Result<()>`: sequences
  mandatory stage records, tracks the active stage/timings, and runs the result
  transaction.

## Invariants and errors

- The pipeline returns success only after the JSON output is committed.
- Stage errors propagate as typed `Error` values; no stage is skipped silently.
- The output is written atomically and never overwrites an existing target.
- `result_ready_for_publication` is synchronized before publication and does not
  claim that the output has already committed; success never depends on a
  post-publication log write.
- Logs include aggregate metrics only. Complete sequences, alleles, configured
  region contents, per-call peaks, alignment strings, and JSON bodies are absent.
- A stage failure is returned unchanged when its stage-aware ERROR record is
  synchronized; if logging also fails, `Error::AnalysisAndLog` reports both
  failures.

## Dependencies

- `input`, `logger`, `basecalling`, `signal_processing`, `quality_control`,
  `alignment`, `variant_calling`, `report`.
- `cli` for `AnalyzeArgs`.
- `error` for `Result`.

## Biological semantics

The stage order reflects the analysis flow: decode the chromatogram, re-call
bases, annotate rolling SNR and candidate-noisy regions, score quality and trim
ends, align the retained read, and extract primary-sequence differences.

## Tests

No dedicated unit tests; `tests/analyze.rs` verifies ordered stage events,
aggregate metrics including signal-window/region counts, payload omissions,
removed-variant reasons, warning levels,
and stage-aware failures across the complete pipeline.

## Status

Implemented.
