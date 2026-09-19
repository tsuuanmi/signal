# `src/bin/signal-validation.rs`

## Purpose

Provides the command-line boundary for local validation measurement export.

## Responsibilities

- Parse one non-identifying validation sample ID, one or more AB1 traces, and one reference FASTA.
- Call the public validation API.
- Print only terminal errors and return an operating-system exit code.

## Output

The scientific implementation writes `validation-results/<sample-id>.jsonl`; operational logs use `<sample-id>.validation.log` under the configured log directory.

## Non-responsibilities

No data discovery, manifest parsing, threshold fitting, scientific computation, or production result publication.

## Status

Implemented.
