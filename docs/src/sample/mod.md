# `src/sample/mod.rs`

## Purpose

Defines the sample-level scientific evidence aggregation boundary shared by production and validation tooling.

## Responsibilities

- Expose deterministic production aggregation of independently produced `ReadObservation[]` into compact `SampleEvidence`.
- Expose dense all-covered locus evidence internally for validation measurements after the same compatibility checks and deterministic SHA ordering.
- Keep validation/order, coverage topology, overlap admission, generic locus aggregation, call-signal projection, contribution policy, nucleotide support/geometry, and variant aggregation in focused child modules.

## Non-responsibilities

No input loading, logging, publication, threshold fitting, consensus projection, or metadata-driven pairing.

## Status

Implemented.
