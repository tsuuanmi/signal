# `src/model/alignment.rs`

## Purpose

Defines selected alignment records, orientation, reference segments, and alignment metrics.

## Responsibilities

- Represent forward/reverse orientation relative to the supplied reference.
- Project a trace-strand canonical base to the reference strand.
- Project A/C/G/T channel-height order to reference orientation for reviewer-facing evidence.
- Represent 0-based half-open mapped reference segments and circular-origin wrap state.

## Orientation projection

Forward evidence is unchanged. Reverse evidence complements base labels and reorders A/C/G/T channel heights as raw T/G/C/A into reference-oriented A/C/G/T.

## Status

Implemented.
