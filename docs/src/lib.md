# `src/lib.rs`

## Purpose

Defines the Signal library boundary and dispatches parsed commands.

## Responsibilities

- Declare the internal subsystem graph.
- Expose the intentional CLI, configuration, error, and model surfaces.
- Route commands to `pipeline`.

## Inputs and outputs

Accepts `cli::Cli`; returns `error::Result<()>`.

## Key types and functions

- `run(cli: Cli) -> Result<()>`: dispatches one `Command::Analyze` to
  `pipeline::analyze`.

## Invariants and errors

The library forbids unsafe Rust. It does not print or select process exit codes.
Pipeline errors are preserved for the binary boundary.

## Dependencies

- `cli`, `config`, `error`, `model` are public.
- `alignment`, `basecalling`, `pipeline`, `quality_control`, `reference`,
  `report`, `trace`, `variant_calling` are private.

## Apollo mapping

Replaces the routing role of `apollo/src/apollo.cpp`; it does not reproduce
Apollo's command set.

## Requirements and decisions

ADR-0001, ADR-0002, ADR-0006; `SRS-IN-010`, `SRS-NFR-001`, `SRS-NFR-006`.

## Tests

`tests/cli.rs`, `tests/docs_mirror.rs`.

## Status

Implemented.
