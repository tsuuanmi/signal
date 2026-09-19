# `src/model/sample_result.rs`

## Purpose

Defines serializable `signal.sample_evidence/v6` result records.

## Responsibilities

Represent sample identity, shared provenance, the read registry with per-read trace-integrity evidence, run-length coverage/orientation topology, pairwise overlap/admission evidence, sparse differential loci, and normalized variant support.

Public overlap, locus, and variant records refer to reads by unique human-readable filename stem rather than numeric registry index. Variant call evidence contains only role, reference-oriented base, four-channel peaks, and quality.

## Coordinates

Locus/variant `position` is 1-based. Read reference segments are 0-based half-open. Internal call/PLOC coordinates are not part of this public contract.

## Status

Implemented.
