# `src/report/json.rs`

## Purpose

Assembles the compact `signal.analysis/v3` document and serializes it
deterministically.

## Responsibilities

- Build the immutable `AnalysisResult` from the completed stage outputs.
- Derive the compact `WarningSummaryResult` from the calls, alignment, and the
  count of typed excluded-variant diagnostics; diagnostic details remain outside
  deterministic JSON.
- Delegate projection of variant-associated calls to the `variant` submodule.
- Serialize to pretty JSON with a trailing newline.

## Non-responsibilities

No filesystem access, atomic publication, variant-call projection, or algorithm
logic.

## Key types and functions

- `CompletedAnalysis`: the inputs consumed to build the document.
- `build(completed) -> Result<AnalysisResult>`: assembles the v3 document.
- `serialize(result) -> Result<Vec<u8>>`: deterministic JSON bytes with a trailing
  newline.
- `warning_summary(...) -> WarningSummaryResult`: counts non-fatal conditions
  instead of collecting verbose per-call messages, and records the boolean
  `reference_origin_wrap` flag for an origin-crossing circular alignment.

## Invariants and errors

- `schema_version` is `signal.analysis/v3` and the variant method is
  `signal.primary_difference/v3`.
- Serialization is deterministic; identical inputs produce identical bytes.
- Optional `position` and `vendor_score` fields are skipped when absent.
- Variant projection errors (missing call/quality index) return `Error::Report`.
- Serialization failures return `Error::Serialize`.

## Dependencies

- `config` for `Config`.
- `model::result`, `model::alignment`, `model::basecalls`, `model::quality`,
  `model::reference`, `model::trace`, `model::variant`.
- `variant` for projecting variant-associated calls.
- `error` for `Result`.
- `serde_json` for serialization.

## Biological semantics

The document records the selected sequence, quality/trim bounds, the winning
alignment, and reported variants with only their local peak/quality evidence, plus
provenance and configuration identity for reproducibility. Full sample arrays,
per-call tables, and losing orientation candidates are deliberately omitted.

## Tests

Integration tests exercise deterministic report assembly and key output fields. `scripts/validate_analysis_schema.py` and CI validate the schema, bundled example, optional generated results, and negative call-mapping shapes.

## Status

Implemented.
