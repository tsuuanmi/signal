# CI and Verification Lanes

CI exists to protect known invariants, not to maximize the number of badges.

## Pull-request lane

The fast required lane should cover deterministic checks that are expected on every code change:

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

Repository-specific reference/config/docs-mirror checks remain required when present.

## Extended lane

Checks with higher runtime or specialized toolchains may run on a schedule, release candidate, or targeted change:

- fuzz campaigns;
- mutation testing;
- property-test expansion;
- dependency/license/advisory audit;
- performance regression measurements;
- approved real-AB1 regression corpus.

A check should be added only when its protected failure mode is documented.

## Failure ownership

- formatter/lint/compiler failure: engineering defect;
- schema/example mismatch: contract defect;
- synthetic test failure: algorithm/implementation regression;
- real-trace disagreement: scientific validation issue requiring analysis, not automatic suppression;
- dependency audit failure: supply-chain/release blocker unless explicitly reviewed.

See [release operations](release.md) and [validation](../validation/README.md).
