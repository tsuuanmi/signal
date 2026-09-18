# ADR-0006: Separate Bulk Research Evidence From Compact Results

- **Status:** Accepted for research
- **Date:** 2026-09-18

## Context
Profile-aware research may need dense per-call or per-channel evidence. Current Signal result schemas are deliberately compact and stable.

## Decision
Bulk review/profile/training evidence shall not be added to compact production schemas by default. If promoted, it must use an explicit opt-in and independently versioned contract.

## Consequences
Research can retain rich evidence without destabilizing the authoritative analysis result. Interchange formats remain projections rather than alternate scientific implementations.
