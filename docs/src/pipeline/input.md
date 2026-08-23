# `src/pipeline/input.rs`

## Purpose

Validates one-file cardinality and path types, then loads every input exactly
once.

## Responsibilities

- Require the AB1 trace and reference to be non-empty regular files.
- Load the strict configuration and require its source file to exist.
- Derive the output path as `results/<trace-stem>.json` and reject an existing
  target or a parent path that exists but is not a directory.
- Load the chromatogram and reference into validated models.

## Non-responsibilities

No directory scanning, globs, manifests, or multi-file discovery.

## Key types and functions

- `Inputs`: the loaded `Config`, `Chromatogram`, `Reference`, and output path.
- `load(args) -> Result<Inputs>`: the entry point.
- `require_regular_file(path, kind) -> Result<()>`: path-type validation.
- `output_path(trace) -> Result<PathBuf>`: joins the trace file stem to `results/`
  as `results/<trace-stem>.json`.
- `trace_stem(trace) -> Result<&str>`: validates and shares the UTF-8 stem used by
  result and log paths.

## Invariants and errors

- The trace and reference must be non-empty regular files; otherwise
  `Error::Read` or `Error::Path`.
- The output target must not already exist; otherwise `Error::Path`.
- The output parent path must not exist as a non-directory; otherwise
  `Error::Path`. A missing parent is permitted and created at publication time.
- The configuration source file must exist; otherwise `Error::Read`.

## Dependencies

- `cli` for `AnalyzeArgs`.
- `config`, `reference`, `trace`.
- `model::reference` and `model::trace`.
- `error` for `Error`/`Result`.

## Biological semantics

None; this module is purely about input validation and loading.

## Tests

No dedicated unit tests; behavior is exercised through the integration tests.

## Status

Implemented.
