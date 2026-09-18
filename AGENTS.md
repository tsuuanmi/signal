# AGENTS.md — Signal Agent Guide

This file is a router for coding agents working on Signal. Detailed system knowledge belongs in `docs/`; do not duplicate it here.

## 1. Start here

Before changing behavior:

1. read [docs/README.md](docs/README.md);
2. locate the relevant SRS requirements in [docs/requirements.md](docs/requirements.md);
3. read [architecture/invariants.md](docs/architecture/invariants.md) and relevant ADRs;
4. read the relevant current method/contract documentation;
5. read the matching `docs/src/` manual and affected source files in full;
6. inspect relevant tests and [traceability.md](docs/traceability.md).

Research under `docs/research/` is non-normative. Do not implement a research proposal as production behavior unless it has been promoted into root production documentation.

## 2. Authority and conflicts

Use the authority model in [documentation governance](docs/governance/documentation.md).

Important distinction:

- SRS/contracts describe intended production behavior.
- Source describes what the current revision actually executes.
- ADRs explain decisions.
- `docs/src` explains implementation ownership.
- Roadmap/research describe future or exploratory work.

If source and normative docs disagree, surface the mismatch. Do not silently redefine the contract to match the implementation or vice versa.

## 3. Change philosophy

Prefer the smallest coherent production-ready change.

Do not:

- add speculative features or abstractions;
- preserve obsolete compatibility paths unless required by the current specification;
- mix unrelated refactors with the requested change;
- silently weaken biological semantics to make tests pass;
- turn observational evidence into stronger biological claims;
- modify public schemas/config/CLI behavior without updating their contracts.

Existing known-good behavior is the development baseline. The core confidence floor is not a reason to remove validated capabilities.

## 4. Scientific changes

Review every scientific change through three lenses:

- **signal processing:** what was measured and what transformation is justified?
- **biology:** what claim does the evidence actually support?
- **engineering:** how is the invariant represented, checked, tested, and versioned?

Preserve the invariants in [docs/architecture/invariants.md](docs/architecture/invariants.md).

In particular:

- decoded analyzed channels are immutable source evidence;
- unresolved evidence remains unresolved;
- mixed signal is not automatically heteroplasmy/genotype/contamination;
- a single trace is read-level evidence;
- reverse-strand processing preserves original call identity;
- coordinate domains must not be mixed implicitly.

## 5. Rust rules

Signal uses Rust as correctness architecture.

Production code:

- forbids `unsafe`;
- avoids `unwrap`/`expect` for recoverable external conditions;
- uses typed errors;
- validates untrusted sizes/offsets before slicing/allocation;
- prefers explicit typed states when they remove a real coordinate/strand/topology/state failure mode;
- keeps scientific transformations separate from filesystem/logging side effects.

Do not add type-level complexity that does not eliminate a concrete failure mode.

## 6. Documentation synchronization

Update documentation in the same change when behavior changes.

Typical impact:

- scientific behavior -> SRS + method docs + `docs/src` + tests + validation impact;
- architecture boundary -> architecture + ADR when decision-worthy + `docs/src`;
- CLI/config/schema -> SRS + contract + schema/example + tests + changelog;
- source ownership only -> matching `docs/src` manual;
- research only -> `docs/research/<topic>/`; do not change production contracts until promotion.

Every mirrored `src/**/*.rs` file must keep its same-relative-path manual under `docs/src/` according to repository policy.

## 7. Verification

Use the repository's locked Python environment and Rust gates.

```bash
uv sync --locked

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

Run additional targeted validation when the change affects parser boundaries, schemas, scientific algorithms, real-trace behavior, dependencies, performance, or release evidence. See [CI lanes](docs/operations/ci.md).

Do not add a gate merely for completeness; every gate should protect a named failure mode.

## 8. Git/worktree safety

Keep changes scoped to the task.

- inspect current status/diff before destructive actions;
- do not use destructive repository-wide reset/clean operations;
- do not stage unrelated files;
- do not create backup files inside the repository;
- do not modify generated artifacts directly when a generator/source exists;
- treat dependency and lockfile changes as reviewed code.

## 9. Before finalizing

Confirm:

- the changed behavior matches the relevant SRS/ADR/method/contract;
- affected `docs/src` manuals are current;
- tests protect the intended invariant rather than merely execute the line;
- schemas/examples validate when affected;
- research has not been mistaken for production authority;
- changelog is updated for user-visible behavior;
- the final diff contains no unrelated changes.

Report what changed, verification performed, tests skipped or failed, documentation/changelog impact, and remaining scientific or engineering risks.
