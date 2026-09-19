# `src/alignment/orient.rs`

## Purpose

Selects the uniquely best forward or reverse-complement alignment and projects circular reference coordinates.

## Responsibilities

- Align both orientations of the QC-retained sequence.
- Map oriented query indexes back to original call indexes.
- Reject orientation or placement ties and configured alignment-quality failures.
- Derive reference segments from the selected alignment.
- Split circular coverage into two segments and set `wraps_origin` when the alignment crosses the reference origin.

## Post-trim coverage

Alignment consumes `QualityControlResult.retained_sequence`. Therefore emitted reference segments describe mapped coverage **after end trimming**, not the untrimmed decoded call span.

## Circular origin

For a circular reference, `wraps_origin=true` means the selected alignment passes from the end of the reference back to position 1. The public result then contains two 0-based half-open reference segments.

## Status

Implemented.
