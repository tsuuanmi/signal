# Contributing

## Change discipline

Read the relevant top-level contract and every affected source/manual file before editing. Keep modules cohesive and dependencies pointing toward `model`, `config`, and `error`. Do not add compatibility wrappers, hidden fallbacks, sample-specific corrections, or filesystem side effects to scientific modules.

Every `src/x.rs` change requires review of `docs/src/x.md`. New Rust files and same-path manuals arrive together. Public CLI/config/schema/method/coordinate/biological changes require SRS, ADR/compatibility, validation, README, and changelog review.

## Data safety

Ignored `data/` is optional local material. Never commit, copy, inspect for a task, or derive a golden from patient/sample AB1 data without the approval/provenance record in `docs/data.md`. Synthetic fixtures are preferred. Analysis JSON contains sequence/signal evidence and follows the same handling policy.

## Configuration and output

Scientific settings belong in strict `config/signal.toml`; do not add per-setting environment overrides. `.env` remains ignored and is never parsed by Signal. JSON schema changes are versioned contracts. Signal must never overwrite an existing result or leave a partial result.

## Checks

```bash
uv sync --locked
uv run ruff format --check scripts/
uv run ruff check scripts/
uv run basedpyright scripts/
uv run python scripts/validate_analysis_schema.py
cargo fmt --all --check
cargo check --all-targets
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cargo doc --no-deps
```

The validator checks the Draft 2020-12 schema, example, and negative variant-call shapes. Also parse TOML, check links/reference identity, and review `git diff`/`git status`. Do not commit unless explicitly requested.
