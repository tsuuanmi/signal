# `src/validation/mod.rs`

## Purpose

Defines the explicit library boundary for local validation measurement export.

## Responsibilities

- Define `ValidationExportRequest` with research sample ID, trace paths, and reference path.
- Route validation export to the internal pipeline implementation.

## Non-responsibilities

No CLI parsing, scientific computation, threshold selection, or publication logic.

## Status

Implemented.
