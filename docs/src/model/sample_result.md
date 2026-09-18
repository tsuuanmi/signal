# `src/model/sample_result.rs`

## Purpose

Defines the serializable `signal.sample_evidence/v1` result records.

## Responsibilities

Represent sample identity, shared reference/configuration provenance, reads with shared compact selected-alignment summaries, covered-locus observations, and normalized variant support with read names/SHA identities, eligibility/exclusion reasons, and concise call pointers, without raw trace data or consensus sequence.

## Non-responsibilities

No scientific aggregation, filtering, interpretation, filesystem access, or JSON serialization logic.

## Coordinates

Locus/variant `position` is 1-based. Read reference segments are 0-based half-open. Original call `index` and `ploc` values are 0-based; mapped call `position` values are 1-based.

## Status

Implemented.
