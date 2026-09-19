# `src/model/locus_evidence.rs`

## Purpose

Defines immutable basecall-independent evidence at one PLOC-defined locus.

## Responsibilities

- Represent raw co-located A/C/G/T channel values, local baseline/noise, corrected amplitudes, and SNR.
- Preserve the source PLOC window and the independently refined event sample.
- Represent an optional normalized `EvidenceProfile` whose A/C/G/T weights come directly from corrected signal mass.

## Non-responsibilities

No primary/IUPAC calling, threshold membership, quality scoring, alignment, variant interpretation, genotype, heteroplasmy, or reporting.

## Invariants

A/C/G/T arrays follow `Nucleotide::ALL`. Corrected amplitudes and SNR are non-negative. A profile exists only when corrected signal mass is positive and then sums to one apart from floating-point roundoff.

## Status

Implemented.
