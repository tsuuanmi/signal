# `src/pipeline/input.rs`

## Purpose

Validates one-file cardinality and path types, then loads every input exactly
once.

## Responsibilities

- Require command-specific AB1 and optional analysis-reference inputs to be
  non-empty regular files.
- Load the strict configuration and require its source file to exist.
- Derive `results/<trace-stem>.json` for analysis or
  `results/<trace-stem>.basecalls.json` for basecall, rejecting an existing target
  or a parent path that exists but is not a directory.
- Load the chromatogram and, only for analysis, the reference into validated models.

## Non-responsibilities

No directory scanning, globs, manifests, or multi-file discovery.

## Key types and functions

- `AnalysisInputs`: loaded config, chromatogram, reference, and analysis target.
- `BasecallInputs`: loaded config, chromatogram, and reference-free target.
- `load_analysis(args)` and `load_basecall(args)`: command-specific entry points.
- `require_regular_file(path, kind)`: shared path-type validation.
- `trace_stem(trace) -> Result<&str>`: validates and shares the UTF-8 stem used by
  result and log paths.

## Invariants and errors

- The trace, and the reference for analysis, must be non-empty regular files;
  otherwise `Error::Read` or `Error::Path`.
- The output target must not already exist; otherwise `Error::Path`.
- The output parent path must not exist as a non-directory; otherwise
  `Error::Path`. A missing parent is permitted and created at publication time.
- The configuration source file must exist; otherwise `Error::Read`.

## Dependencies

- `cli` for `AnalyzeArgs` and `BasecallArgs`.
- `config`, `reference`, `trace`.
- `model::reference` and `model::trace`.
- `error` for `Error`/`Result`.

## Biological semantics

None; this module is purely about input validation and loading.

## Tests

No dedicated unit tests; behavior is exercised through the integration tests.

## Status

Implemented.
