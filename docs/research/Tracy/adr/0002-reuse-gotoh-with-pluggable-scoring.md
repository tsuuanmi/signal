# ADR-0002: Reuse Gotoh With Generalized Scoring

- **Status:** Accepted for research
- **Date:** 2026-09-18

## Context
Signal already has a bounded deterministic affine-gap Gotoh implementation. Tracy's useful difference is the scoring input: profiles can be aligned without requiring a separate DP architecture.

## Decision
Generalize substitution scoring around one authoritative Gotoh state-transition/traceback implementation. Do not introduce a second long-lived alignment engine merely to support profiles.

## Consequences
Sequence and profile alignment share gap, traceback, coordinate, orientation, and circular-reference semantics. Scoring must define deterministic numeric and tie-breaking behavior.
