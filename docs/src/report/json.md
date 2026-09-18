# `src/report/json.rs`

## Purpose

Assembles compact `signal.analysis/v5` and provides deterministic serialization
shared by typed result contracts.

## Responsibilities

- Consume `CompletedAnalysis`, containing the reference record and one complete
  `ReadObservation` produced by the scientific pipeline. The observation owns
  input and configuration identities.
- Validate that the observation's reference identity matches the supplied
  reference record.
- Delegate merged noisy-region projection to `report::signal`; individual
  signal windows and maximum secondary SNR remain internal.
- Project the selected alignment into orientation, callable bases/identity,
  unresolved bases, gap opens, reference segments, and wrap status only.
- Build deterministic provenance and read metadata without trace filename or
  sequence strings.
- Derive `WarningSummaryResult` from call categories and excluded candidates,
  then delegate variant evidence projection to `report::variant`.
- Serialize pretty JSON with one trailing newline.

## Non-responsibilities

No filesystem access, atomic publication, variant-call projection details,
signal feature computation, or scientific decision logic.

## Key types and functions

- `CompletedAnalysis`: report context containing the reference and one complete
  one-read observation.
- `build_analysis(completed) -> Result<AnalysisResult>`: validates the model and
  assembles v5 without filesystem side effects.
- `serialize<T: Serialize>(result) -> Result<Vec<u8>>`: deterministic pretty
  JSON bytes with a trailing newline for analysis and basecall results.
- `warning_summary(...) -> WarningSummaryResult`: counts unresolved primary
  calls, multi-channel unresolved calls, and excluded variant candidates.

## Invariants and errors

- `schema_version` is `signal.analysis/v5`.
- Provenance contains input SHA-256, reference identity, and configuration
  SHA-256; software/build identity, method identifiers, and trace filename are
  absent.
- The report rejects a `ReadObservation` whose reference checksum does not match
  the supplied `Reference`.
- Read output contains only call count and trim bounds; complete primary,
  ambiguity, and retained sequences are absent.
- Alignment output contains no score, columns, gapped rows, or operation runs.
- Operational vendor-disagreement/origin-wrap accounting is not part of this
  projection and remains owned by pipeline logging.
- Variant projection failures return `Error::Report`; serialization failures
  return `Error::Serialize`.

## Dependencies

- `error::Result`.
- `model::basecalls::BaseCalls`, `model::read_observation::ReadObservation`,
  `model::reference::Reference`, and compact result records from
  `model::result`.
- `report::signal` and `report::variant` for focused projection logic.
- `serde`/`serde_json` for deterministic serialization.

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
