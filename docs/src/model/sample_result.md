# `src/model/sample_result.rs`

## Purpose

Defines the serializable `signal.sample_evidence/v2` result records.

## Responsibilities

Represent sample identity, shared reference/configuration provenance, the deterministic read registry, sparse differential loci, and normalized variant support without raw trace arrays or consensus sequence.

Locus and variant observations reference reads by 0-based registry index instead of repeating read name, SHA-256, or orientation.

## Non-responsibilities

No scientific aggregation, filtering, interpretation, filesystem access, or JSON serialization logic.

## Coordinates

Locus/variant `position` is 1-based. Sample `read`, original call `index`, and `ploc` are 0-based. Read reference segments are 0-based half-open. Mapped call `position` values are 1-based.

## Status

Implemented.
