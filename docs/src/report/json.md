# `src/report/json.rs`

## Purpose

Assembles compact `signal.analysis/v5` and provides deterministic serialization
shared by typed result contracts.

## Responsibilities

- Consume `CompletedAnalysis`, containing config, trace, reference, base calls,
  signal analysis, quality control, selected alignment, and variant calling.
- Delegate merged noisy-region projection to `report::signal`; individual signal
  windows and maximum secondary SNR remain internal.
- Project the selected alignment into orientation, callable bases/identity,
  unresolved bases, gap opens, reference segments, and wrap status only.
- Build deterministic provenance and read metadata without trace filename or
  sequence strings.
- Derive `WarningSummaryResult` from call categories, excluded candidates, and
  alignment wrap state, then delegate variant evidence projection to `variant`.
- Serialize pretty JSON with one trailing newline.

## Non-responsibilities

No filesystem access, atomic publication, variant-call projection details, signal
feature computation, or scientific decision logic.

## Key types and functions

- `CompletedAnalysis`: all completed internal stage outputs consumed by assembly.
- `build_analysis(completed) -> Result<AnalysisResult>`: assembles v5 without
  filesystem side effects.
- `serialize<T: Serialize>(result) -> Result<Vec<u8>>`: deterministic pretty JSON
  bytes with a trailing newline for analysis and basecall results.
- `warning_summary(...) -> WarningSummaryResult`: counts the three public JSON
  categories: unresolved primary calls, multi-channel unresolved calls, and
  excluded variant candidates.

## Invariants and errors

- `schema_version` is `signal.analysis/v5`.
- Provenance contains software version, input SHA-256, reference identity, and
  configuration SHA-256; method identifiers and trace filename are absent.
- Read output contains only call count and trim bounds; complete primary,
  ambiguity, and retained sequences are absent.
- Alignment output contains no score, columns, gapped rows, or operation runs.
- Operational vendor-disagreement/origin-wrap accounting is not part of this
  projection and remains owned by pipeline logging.
- Variant projection failures return `Error::Report`; serialization failures
  return `Error::Serialize`.

## Dependencies

- `config` for `Config`.
- `model::alignment`, `model::basecalls`, `model::quality`, `model::reference`,
  `model::result`, `model::signal`, `model::trace`, and `model::variant`.
- `signal` and `variant` for shared noisy-region and analysis-call projection.
- `error` for `Result`; `serde_json` for serialization.

## Biological semantics

The document reports merged candidate-noisy regions, the retained call interval,
a compact alignment quality summary, and normalized variants with only their
essential supporting/flanking call evidence. Full sample arrays, rolling windows,
sequence strings, detailed alignment rows, per-channel peaks, per-call penalties,
and vendor quality values are deliberately omitted.

## Tests

Integration and schema tests exercise deterministic v5 assembly, optional
supporting-evidence fields, warning counts, and invalid call-mapping shapes.

## Status

Implemented.
