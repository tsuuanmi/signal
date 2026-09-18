# Development Readiness

This document answers one question:

> Is Signal's active scientific-core MVP defined clearly enough to begin implementation without reopening the product architecture on every change?

It is not a production-release checklist. Production readiness is governed separately by [ADR-0018](adr/0018-production-readiness-release-contract.md).

## Three design lenses

Every active MVP decision is reviewed through three complementary lenses.

| Lens | Core question | MVP concern |
|---|---|---|
| Signal processing | What does the chromatogram actually measure, and what transformation is justified? | Preserve analyzed A/C/G/T evidence, use explicit PLOC-defined loci for the current method, avoid unvalidated denoising or calibration. |
| Biology | What biological statement does the evidence support? | Conservative primary calls, explicit unresolved/ambiguity states, simple read-level SNVs only, no heteroplasmy/genotype/clinical inference. |
| Engineering | How do we make the intended invariants hard to violate? | Typed stages, checked input, deterministic behavior, explicit coordinate systems, versioned schemas, tests and CI gates. |

A change is ready only when the three views agree on the same concept.

## Active MVP boundary

```text
AB1
 ↓
validated ABIF/analyzed-channel decode
 ↓
signal-derived re-calling at validated PLOC loci
 ↓
basic deterministic end QC / trimming
 ↓
forward/reverse alignment to one short reference
 ↓
simple canonical SNVs
 ↓
versioned JSON
```

The following are not required to begin or accept this core MVP:

- release-critical indel calling;
- repeat/poly-C special handling;
- quantitative heteroplasmy or genotype inference;
- sample consensus or multi-read aggregation;
- haplogroup inference/correction;
- ML;
- advanced denoising, calibration, or independent locus discovery.

Existing code for deferred capabilities may remain, but it does not enlarge the active MVP contract.

## Stage contracts that must be stable before implementation

### Decode

Input:
- one bounded ABIF/AB1 byte stream.

Output:
- canonical analyzed A/C/G/T channel arrays;
- validated PLOC loci;
- optional vendor PBAS/PCON evidence;
- source identity.

Invariant:
- no downstream stage receives malformed channel order, mismatched channel lengths, invalid PLOC coordinates, or unchecked binary offsets.

### Base calling

Input:
- validated chromatogram;
- explicit basecalling configuration.

Output:
- ordered per-locus calls;
- primary sequence;
- ambiguity state;
- retained per-locus evidence sufficient to explain the call.

Invariant:
- current MVP is re-calling at PLOC-defined loci, not de novo event discovery;
- vendor PBAS does not determine the final Signal call;
- unresolved evidence remains unresolved.

### QC / trimming

Input:
- base-called read and its evidence.

Output:
- one retained half-open interval plus documented per-call quality evidence.

Invariant:
- trimming affects read ends only for the MVP;
- any quality score is described according to what has actually been validated;
- internal poor-quality regions are not silently rewritten.

### Alignment

Input:
- retained primary sequence;
- one validated short reference.

Output:
- selected orientation;
- mapped reference span;
- original-call coordinate mapping.

Invariant:
- forward and reverse candidates are evaluated explicitly;
- call identity survives orientation changes;
- ambiguous placement fails or remains explicit.

### Simple SNV calling

Input:
- selected alignment plus original call evidence.

Output:
- canonical A/C/G/T primary-sequence substitutions only.

Invariant:
- unresolved query states do not become variants;
- reported position and allele are on the reference strand;
- every reported SNV maps back to the supporting trace call.

### JSON contract

Input:
- completed typed analysis result.

Output:
- one closed, versioned, schema-valid JSON document.

Invariant:
- coordinate conventions are explicit;
- observation and interpretation are not conflated;
- output contains enough provenance and direct evidence to audit the result without exposing unstable implementation internals.

## What may still evolve during implementation

Development readiness does not require prematurely freezing every algorithmic constant.

The following may be refined through focused implementation and real-trace validation:

- exact peak-window edge behavior;
- exact secondary-evidence threshold;
- conservative weak-signal rule;
- QC/trimming threshold values;
- alignment scoring defaults;
- compact presentation details that do not change the biological claim or coordinate semantics.

A change in one of these areas does not require an architectural reset if the stage contract above remains intact.

## Start-development gate

The project is ready to begin focused MVP implementation when:

- [x] the vertical slice is fixed;
- [x] signal evidence and biological claims are separated;
- [x] PLOC-based re-calling is explicitly the current basecalling boundary;
- [x] input, stage, coordinate, error, and output boundaries are defined;
- [x] simple SNVs are the first release-critical variant class;
- [x] harder biological interpretation is explicitly deferred;
- [x] Rust engineering principles and release-quality direction are documented;
- [ ] normative SRS is reconciled so deferred capabilities are not accidentally treated as core MVP acceptance criteria;
- [ ] the first approved real-AB1 validation set and expected truth records are identified.

## Current assessment

**Architecture: ready.**

The system boundaries are clear enough to begin implementation work without needing another broad architecture brainstorm.

**Core scientific implementation: ready to start in small slices.**

Development should proceed stage-by-stage, beginning with decode/basecalling validation and avoiding feature expansion.

**MVP acceptance: not yet ready.**

The remaining blockers are requirement-profile cleanup and real-trace validation evidence, not missing architectural ideas.
