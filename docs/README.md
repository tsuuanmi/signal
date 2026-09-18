# Signal Documentation

This is the documentation entry point for humans and coding agents.

Signal documentation is organized by **authority and responsibility**. Keep one
authoritative home for each concept; do not create parallel notes that restate a
schema, source manual, or accepted decision.

## Read order for a change

1. [Requirements](requirements.md) — intended system behavior.
2. [Architecture](architecture/README.md) and [invariants](architecture/invariants.md) — boundaries and cross-cutting truths.
3. [ADRs](adr/README.md) — accepted decisions and rationale.
4. [Methods](methods/README.md) — current scientific/algorithmic semantics.
5. [Contracts](contracts/README.md) — public interfaces and coordinate semantics.
6. [Source manuals](src/README.md) plus affected source — implementation ownership.
7. [Traceability](governance/traceability.md) and [validation](validation/README.md) — protected evidence and verification.

## Authority

| Documentation | Role |
|---|---|
| [SRS](requirements.md) | normative intended behavior |
| JSON schemas / checked configuration | exact machine-visible contract |
| [ADRs](adr/README.md) | decisions and rationale |
| [Architecture](architecture/README.md) | boundaries and invariants |
| [Methods](methods/README.md) | current scientific/algorithmic semantics |
| source code | executable behavior of the current revision |
| [`docs/src`](src/README.md) | descriptive implementation ownership; must track source |
| [Validation](validation/README.md) | how claims are verified |
| [Roadmap](roadmap.md) | future direction; non-normative |
| [Research](research/README.md) | exploratory work; non-normative |

If source and normative production documentation disagree, surface the mismatch
and resolve it in the owning change. See
[documentation governance](governance/documentation.md).

## Production documentation

- [Requirements / SRS](requirements.md)
- [Architecture](architecture/README.md)
- [ADR index](adr/README.md)
- [Current methods](methods/README.md)
- [Public contracts](contracts/README.md)
- [Source manuals](src/README.md)
- [Validation](validation/README.md)
- [Operations](operations/README.md)
- [Governance](governance/README.md)
- [Traceability](governance/traceability.md)
- [Glossary](glossary.md)
- [Roadmap](roadmap.md)

## Research

Research lives only under [`docs/research/`](research/README.md) and does not
change production behavior until promoted through the production SRS/ADR/contract
process.

- [Signal research](research/Signal/README.md)
- [Tracy research](research/Tracy/README.md)
