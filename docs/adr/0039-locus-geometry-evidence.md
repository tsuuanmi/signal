# ADR-0039: Preserve local PLOC geometry as observation evidence

- **Status:** Accepted
- **Date:** 2026-09-19

## Context

Signal already validates a strictly increasing PLOC series, derives midpoint locus
windows, refines one signal event inside each window, and publishes whole-trace
minimum/median/maximum PLOC spacing as integrity evidence.

The per-locus evidence model did not retain how far the refined event moved from
its vendor PLOC or the spacing immediately surrounding that locus. Those local
geometry observations are useful for validating compressed/expanded spacing,
bounded event refinement, and possible neighbor interference before any artifact
classifier or sample-contribution policy is introduced.

A global spacing summary cannot recover which individual locus had unusual local
geometry.

## Decision

Each `LocusEvidence` retains three basecall-independent geometry observations in
trace-sample units:

~~~text
event_ploc_distance
minimum_adjacent_ploc_spacing
maximum_adjacent_ploc_spacing
~~~

`event_ploc_distance` is the absolute distance between the refined event sample
and the authoritative PLOC anchor.

Adjacent spacing is calculated from the immediately previous and next PLOC when
present. At an edge locus the one available spacing is both the minimum and
maximum. A locus with no neighbor would retain both spacing values as absent.

Geometry invariants require:

- event/PLOC distance exactly matches the stored coordinates;
- adjacent spacing is positive when present;
- minimum and maximum spacing are either both present or both absent;
- minimum spacing is not greater than maximum spacing.

The same geometry observations are preserved in internal `CallSignalEvidence`
so sample reconciliation does not need to revisit trace internals.

These values are orientation-invariant and therefore are not complemented or
reordered for reverse reads.

## Production observability

Sample aggregation logs aggregate maximum event/PLOC distance and minimum/maximum
adjacent spacing for retained differential-locus observations and
variant-associated calls.

These values remain observation-only.

## Consequences

- Local spacing/refinement evidence survives the read-to-sample boundary.
- Compressed/expanded spacing and neighbor-interference research can use explicit
  geometry instead of reconstructing it from filenames, calls, or the reference.
- No geometry threshold, artifact flag, read rejection, variant filter, or
  consensus weight is introduced.
- Public JSON contracts and configuration remain unchanged.

## Non-goals

This decision does not classify compressed peaks, expanded spacing, dye blobs,
neighbor interference, or sequencing error. It does not define local
contribution eligibility, consensus confidence, genotype, or heteroplasmy.
