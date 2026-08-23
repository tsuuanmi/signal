# `src/report/variant.rs`

## Purpose

Projects normalized variants and mapped original calls into the compact v5
variant and supporting-evidence records.

## Responsibilities

- Turn each internal `Variant` into a `VariantResult` containing position,
  reference/alternate alleles, kind, and projected calls.
- Join each `VariantCallMapping` to its original `BaseCall` and `CallQuality` by
  index, validating index consistency.
- Preserve role, original call index, mapped biological position, PLOC, primary,
  and ambiguity symbols.
- For supporting calls only, emit the maximum of the four channel peak heights and
  the uncalibrated relative quality score.
- Convert internal 0-based reference positions to checked one-based report
  positions; inserted supporting calls keep no reference position.

## Non-responsibilities

No document assembly, serialization, atomic publication, peak-position reporting,
per-channel peak projection, vendor-quality projection, normalization, or variant
eligibility decisions.

## Key types and functions

- `project(variants, calls, quality) -> Result<Vec<VariantResult>>`: module entry
  point called by `report::json::build`.
- `project_variant`: drops internal-only contig and emits no report-only
  classification/normalization labels.
- `project_call`: validates the joined call/quality indexes and constructs the
  concise mapped-call record.

## Invariants and errors

- Missing call or quality indexes return `Error::Report`.
- The referenced `BaseCall` and `CallQuality` indexes must equal the mapping index.
- `position` is absent only for inserted supporting calls and otherwise is a
  checked one-based reference coordinate.
- `maximum_peak_height` and `relative_quality` are present exactly for
  `VariantCallRole::Supporting`; flanking calls omit both.
- Maximum peak height uses all four selected channel heights and does not expose
  per-channel values or peak sample positions.

## Dependencies

- `model::basecalls::BaseCalls`.
- `model::coordinate::reference_one_based`.
- `model::quality::QualityControlResult`.
- `model::result::{VariantCallResult, VariantResult}`.
- `model::variant::{Variant, VariantCallMapping, VariantCallRole}`.
- `error` for `Error`/`Result`.

## Biological semantics

Variant alleles and reported positions use the reference strand. Projected call
symbols and PLOC retain the original trace orientation. Supporting SNV and
inserted-base calls carry the two evidence values used by eligibility filtering;
indel flanks remain positional context and do not fabricate supporting peak or
quality evidence.

## Tests

Behavior is exercised through report assembly, schema validation, and end-to-end
variant tests.

## Status

Implemented.
