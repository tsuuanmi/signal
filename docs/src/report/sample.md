# `src/report/sample.rs`

## Purpose

Projects internal `SampleEvidence` into `signal.sample_evidence/v2`.

## Responsibilities

Validate the evidence/reference identity and map domain records into compact deterministic public result records: one read registry, sparse differential loci, and normalized variant support with indexed reads and concise call pointers.

Reuse the shared compact `AlignmentResult` shape rather than defining sample-specific alignment semantics.

## Non-responsibilities

No scientific aggregation, evidence classification, consensus, serialization, logging, or filesystem publication.

## Status

Implemented.
