# Research

`docs/research/` contains structured exploratory work.

Research is deliberately **non-normative**. It may propose requirements, ADRs, architectures, methods, validation plans, or roadmaps, but none of those change current Signal production behavior until promoted into the root production documentation and implemented.

Each substantial research topic should use its own subtree:

```text
docs/research/<topic>/
├── README.md
├── requirements.md       # optional research SRS
├── architecture.md       # optional proposed architecture
├── adr/                  # research-only decisions
├── validation.md         # evidence needed for promotion
├── roadmap.md            # research sequence
└── ... focused notes
```

The Tracy research PR follows this model under `docs/research/Tracy/`.

## Promotion

```text
research finding
  ↓
root ADR (if a decision is needed)
  ↓
root SRS / method / public contract
  ↓
source + docs/src + tests
  ↓
scientific validation
```

A research document should always state what evidence would be required before promotion.
