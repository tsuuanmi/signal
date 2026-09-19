# `src/sample/mod.rs`

## Purpose

Defines the sample-level scientific evidence aggregation boundary.

## Responsibilities

Expose deterministic aggregation of independently produced `ReadObservation[]` into compact `SampleEvidence` while keeping validation/order, coverage topology, overlap admission, locus-difference extraction, reference-oriented profile projection, and variant aggregation in focused child modules.

## Non-responsibilities

No input loading, logging, publication, consensus projection, or metadata-driven pairing.

## Status

Implemented.
