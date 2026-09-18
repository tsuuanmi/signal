# AGENTS.md — Signal Agent Guide

This file is the execution policy for coding agents working on Signal.

It is intentionally short. System knowledge belongs in `docs/`; this file tells agents which sources are authoritative, what to read, how to change the repository safely, and what evidence is required before a change is complete.

## 1. Read before changing

For any behavior change, read in this order:

1. [docs/README.md](docs/README.md) — documentation map and authority model;
2. [docs/requirements.md](docs/requirements.md) — relevant normative SRS requirements;
3. [docs/architecture/invariants.md](docs/architecture/invariants.md) — cross-cutting invariants;
4. relevant [ADRs](docs/adr/README.md);
5. relevant current [method](docs/methods/README.md) and [contract](docs/contracts/README.md) documentation;
6. matching `docs/src/` manual and affected source files in full;
7. relevant tests, schemas, and [traceability](docs/traceability.md).

Do not implement directly from `docs/research/`. Research is non-normative until promoted through root ADR/SRS/contract documentation.

## 2. Authority

Use [documentation governance](docs/governance/documentation.md).

Roles are different:

- **SRS** — intended normative behavior;
- **schemas/contracts** — exact public/machine-visible contract for the named version;
- **ADRs** — why a decision exists;
- **architecture/invariants** — where responsibility belongs and what must remain true;
- **methods** — detailed current scientific/algorithmic semantics;
- **source** — what the current revision actually executes;
- **docs/src** — implementation ownership/manual;
- **validation** — evidence required to trust the behavior;
- **roadmap/research** — future or exploratory work, never current production authority.

If source and normative documentation disagree, surface the mismatch. Do not silently choose one side or rewrite documentation merely to excuse current code.

## 3. Change rule

Prefer the smallest coherent production-ready change.

Every changed line should be traceable to the task.

Do not:

- add speculative features, wrappers, fallback paths, compatibility aliases, or abstractions;
- preserve obsolete behavior unless the current specification requires it;
- mix unrelated cleanup or broad refactors into the task;
- weaken scientific semantics to make a test pass;
- turn an observation into a stronger biological claim;
- change schema, CLI, configuration, coordinate semantics, or public behavior without updating the corresponding contract;
- treat the core confidence floor as a reason to delete known-good existing capabilities.

When touching legacy or misplaced code, leave one clear authoritative implementation rather than parallel old/new paths unless compatibility is explicitly required.

## 4. Three-lens review for scientific changes

Before implementing or approving a scientific behavior change, answer all three:

### Signal processing

- What measurement or derived signal is being used?
- Is the transformation deterministic and justified?
- Is original evidence preserved?
- Are locality, baseline, noise, peak geometry, and coordinate assumptions explicit?

### Biology

- What statement does the evidence support?
- What alternative explanations remain possible?
- What state should remain unresolved?
- Is the output read-level or sample-level?
- Does the change accidentally imply genotype, heteroplasmy, contamination, pathogenicity, or clinical significance?

### Engineering

- Which invariant changes?
- Which type/module owns it?
- What failure mode is prevented?
- Which test or validation evidence demonstrates correctness?
- Does a public contract or algorithm version need to change?

A change is not ready when one lens is missing.

## 5. Core invariants

Always preserve [docs/architecture/invariants.md](docs/architecture/invariants.md).

Especially:

- decoded analyzed A/C/G/T channels are immutable source evidence;
- derived processing never overwrites source evidence;
- vendor PBAS/PCON are evidence, not authoritative Signal calls;
- call index, trace-sample/PLOC position, and biological reference position are different domains;
- reverse processing preserves original call identity;
- unresolved evidence is not a reference call or absence of variation;
- mixed signal is not automatically heteroplasmy/genotype/contamination;
- one trace provides read-level evidence;
- failed core analysis publishes no result;
- versioned public schemas are not mutated incompatibly in place.

## 6. Rust design policy

Signal uses Rust as correctness architecture.

Production code:

- forbids `unsafe`;
- does not use `unwrap`/`expect` for recoverable external conditions;
- uses typed errors and explicit unsupported states;
- checks input-controlled sizes, offsets, arithmetic, and allocations;
- prefers validated constructors/private fields when they prevent invalid states;
- uses newtypes/enums when they prevent real coordinate, topology, strand, or state confusion;
- keeps scientific transformations deterministic and separate from filesystem/logging side effects;
- avoids type-level cleverness that does not eliminate a concrete failure mode.

The goal is not maximal abstraction. The goal is to move important invariants from human memory into forms the compiler and tooling can verify.

## 7. Source and documentation synchronization

When behavior changes, update the affected layers in the same change.

Typical impact:

| Change | Required documentation/evidence |
|---|---|
| scientific algorithm | SRS + method + `docs/src` + tests + validation impact |
| architectural boundary | architecture/invariants + ADR when decision-worthy + `docs/src` |
| CLI/config/schema | SRS + contract/schema/example + tests + changelog |
| coordinate semantics | invariants + coordinate contract + affected schema/method/tests |
| internal ownership only | matching `docs/src` manual |
| research only | `docs/research/<topic>/` only until promotion |

Every mirrored `src/**/*.rs` file must keep its same-relative-path manual under `docs/src/` according to repository policy.

Do not translate source line by line into docs. A source manual should describe responsibility, inputs, outputs, invariants, dependencies, failure modes, algorithm boundary, and traceability.

## 8. Research promotion

Research may contain proposed SRS, ADRs, architectures, algorithms, or roadmaps.

Promotion into production follows:

```text
research evidence
  ↓
root ADR when a decision is needed
  ↓
root SRS / method / public contract
  ↓
implementation + docs/src
  ↓
tests
  ↓
scientific validation
```

Agreement with another tool is useful comparison evidence, not independent biological ground truth.

## 9. Tests and validation

Tests and scientific validation are different.

A green unit/integration suite proves only the properties encoded by those tests. It does not establish biological correctness.

Choose evidence by failure mode:

- parser/input boundary -> malformed/adversarial fixtures and fuzzing where adopted;
- coordinate/state transform -> unit + property/invariant tests;
- schema/serialization -> schema/example validation;
- scientific method -> synthetic boundary cases + approved real-AB1 evidence;
- performance/resource bound -> documented benchmark/memory measurement;
- dependency/release risk -> audit and release evidence.

Never add a testing tool merely for completeness. Each gate must protect a named failure mode.

## 10. Required verification

Use the locked repository environment:

```bash
uv sync --locked
```

Required code gates:

```bash
uv run ruff format --check scripts/
uv run ruff check scripts/
uv run basedpyright scripts/
uv run python scripts/validate_result_schemas.py

cargo fmt --all --check
cargo check --all-targets
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cargo doc --no-deps
```

Run additional targeted or extended checks when the affected failure mode requires them. See [docs/operations/ci.md](docs/operations/ci.md).

For docs-only changes, source compilation/tests may be unnecessary unless the docs change executable contracts, generated/schema validation, or CI-controlled repository invariants.

## 11. Git and repository safety

Keep the current worktree safe and scoped:

- inspect status/diff before editing or destructive operations;
- never use repository-wide destructive reset/clean commands for routine work;
- never stage unrelated files;
- never create backup files inside the repository;
- do not modify generated files directly when an authoritative generator/source exists;
- treat dependency and lockfile changes as code changes;
- do not overwrite another agent's unrelated work;
- do not create compatibility shims merely to avoid updating affected callers.

## 12. Completion checklist

Before finalizing, confirm:

- relevant SRS/ADRs/invariants/methods/contracts were read;
- the implementation matches the intended biological and engineering semantics;
- affected `docs/src` manuals are current;
- relevant tests protect the invariant, not just line coverage;
- public schemas/examples validate when affected;
- research has not been mistaken for production authority;
- user-visible behavior is reflected in the changelog;
- no unrelated changes or stale compatibility paths remain;
- final diff is architecturally coherent.

Report:

- what changed;
- files/modules affected;
- verification performed;
- tests skipped or failed and why;
- documentation/changelog impact;
- remaining scientific or engineering risks.
