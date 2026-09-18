# ADR-0013: Process Each Trace Independently Before Sample Reconciliation

- **Status:** Accepted for research
- **Date:** 2026-09-18

## Context

Tracy's pairwise consensus and multi-trace assembly both decode, basecall, trim,
and construct a profile for each input chromatogram before combining traces.

Signal already has a strict single-trace scientific pipeline. Future sample
analysis must support collections such as HV1F, HV1R, HV2F, and HV3R, including
cross-amplicon overlap.

## Decision

Every trace shall complete the authoritative single-read pipeline before it can
participate in sample-level reconciliation.

The sample layer consumes immutable ReadObservation values. It shall not
re-basecall, silently re-trim, mutate orientation/evidence, or use sample
consensus to repair a read observation.

Read-level rejection/admission remains explicit and independently auditable.

## Consequences

Single-read behavior remains reusable and testable. Sample analysis can evolve
without coupling low-level signal interpretation to the number or identity of
other reads in the sample.

The same AB1 produces the same read observation whether analyzed alone or as
part of a sample.
