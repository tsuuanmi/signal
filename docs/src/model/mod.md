# `src/model/mod.rs`

## Purpose

Owns the validated domain types shared across scientific stages.

## Responsibilities

- Declare the model submodules: `alignment`, `basecalls`, `coordinate`,
  `nucleotide`, `quality`, `reference`, `result`, `signal`, `trace`, and `variant`.
- Provide validated domain vocabulary with no I/O, CLI, configuration loading, or
  algorithm dependencies.

## Non-responsibilities

No filesystem access, argument parsing, logging, or algorithm execution.

## Key types and functions

- `coordinate`: zero-based to one-based conversion.
- `nucleotide`: canonical bases and reverse complement.
- `trace`: four-channel `Chromatogram` plus vendor evidence.
- `basecalls`: primary/ambiguous calls with trace positions.
- `signal`: rolling SNR windows and merged candidate-noisy regions.
- `quality`: quality vector, trim bounds, and QC result.
- `reference`: name, sequence, topology, and checksums.
- `alignment`: orientation, interval, score, and gapped rows.
- `variant`: normalized `Variant`, `VariantKind`, alleles, and mapped calls.
- `result`: complete `AnalysisResult` matching JSON schema v4.

## Invariants and errors

Constructors and loaders enforce aligned vector lengths, valid nucleotide
symbols, explicit coordinate systems, bounded qualities, and equal-length gapped
rows. Model files have no I/O, CLI, configuration loading, or algorithm
dependencies.

## Dependencies

- `serde` for serialization where records are emitted.
- `error` for typed failures in the few fallible conversions.

## Apollo mapping

Replaces loosely coupled `Trace`, `BaseCalls`, `ReferenceSlice`, alignment
arrays, and `Variant` structs with validated Rust types.

## Requirements and decisions

ADR-0002; `SRS-IN-003`, `SRS-CFG-005`, `SRS-BC-005`, `SRS-ALN-005`,
`SRS-VAR-005`, and `SRS-OUT-002`.

## Tests

Focused invariant tests live beside each child implementation; the integration
tests exercise the full model through the pipeline.

## Status

Implemented.
