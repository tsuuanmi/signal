# Validation System

Signal separates software verification from scientific validation.

## Software verification

- unit and integration tests;
- schema/example validation;
- strict configuration validation;
- formatter, compiler, Clippy, rustdoc, and docs-mirror gates;
- adversarial/fuzz/property testing where adopted;
- deterministic and atomic-publication checks.

The authoritative strategy is [../validation.md](../validation.md).

## Scientific validation

Scientific correctness requires evidence that is independent of implementation success.

Use:

- provenanced synthetic fixtures for exact algorithmic boundaries;
- approved real AB1 traces;
- independently established expected sequences/variants where available;
- explicit acquisition/reference/configuration identity;
- documented disagreement analysis.

A green Rust test suite does not by itself establish biological correctness.

Data provenance and privacy rules are defined in [../data.md](../data.md).

Local corpus execution and descriptive research-table preparation are documented under [Signal research](../research/Signal/README.md); neither step by itself establishes a production threshold.

## Release evidence

Production release evidence follows ADR-0018 and must identify the exact source revision, toolchain, artifact, dependency state, automated gates, performance evidence, and real-trace validation status.
