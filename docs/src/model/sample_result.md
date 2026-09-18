# `src/model/sample_result.rs`

## Purpose

Defines the serializable `signal.sample_evidence/v1` result records.

## Responsibilities

Represent sample identity, shared reference/configuration provenance, read placements, covered-locus observations, and normalized event support without raw trace data or consensus sequence.

## Non-responsibilities

No scientific aggregation, filtering, interpretation, filesystem access, or JSON serialization logic.

## Coordinates

Locus/event `position` is 1-based. Read reference segments are 0-based half-open. Original call `index` values are 0-based.

## Status

Implemented.
