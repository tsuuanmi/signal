# `src/pipeline/observation.rs`

## Purpose

Owns the one authoritative reference-guided scientific path from a decoded trace to `ReadObservation`.

## Responsibilities

Run shared read processing, evidence-derived alignment, configured normalized variant calling, stage logging, exclusion diagnostics, and warning aggregation. Both single-read analysis and sample analysis consume this path.

## Non-responsibilities

No input loading, output publication, JSON projection, sample aggregation, or sample interpretation.

## Architectural role

This module removes duplicated read science between command pipelines. `pipeline::analyze` and `pipeline::sample` differ only in orchestration after one-read observation creation.

## Status

Implemented.
