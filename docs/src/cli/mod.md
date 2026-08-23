# `src/cli/mod.rs`

## Purpose

Defines the stable command-line syntax and typed arguments.

## Responsibilities

- Expose `signal analyze <trace.ab1> --reference <fasta>`, including generated help
  and version information. Output is derived deterministically as
  `results/<trace-stem>.json`; no output-path option is accepted.

## Inputs and outputs

Converts operating-system arguments into `Cli`, `Command`, and `AnalyzeArgs`.
Path existence and file content are validated later by input modules.

## Key types and functions

- `Cli`: the top-level parser.
- `Command::Analyze(AnalyzeArgs)`: the single supported command.
- `AnalyzeArgs`: one positional AB1 path and one required `--reference` FASTA path.
  The output path is derived from the trace stem as `results/<trace-stem>.json`.

## Invariants and errors

Argument syntax failures are handled by Clap. The CLI does not run algorithms.
Repeated AB1 arguments, directories as trace input, manifests, globs, and lists
are rejected. `SIGNAL_CONFIG` is process configuration, not a CLI trace input.

## Dependencies

- `clap` for `Parser`, `Args`, and `Subcommand`.

## Apollo mapping

Signal uses one focused command rather than Apollo's six-command surface.

## Requirements and decisions

ADR-0001, ADR-0003, ADR-0007; `SRS-IN-001`, `SRS-IN-010` through
`SRS-IN-012`, and `SRS-CFG-004`.

## Tests

`tests/cli.rs`.

## Status

Implemented.
