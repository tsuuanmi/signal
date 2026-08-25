# Signal

Signal is a focused Rust tool for deterministic Sanger ABIF/AB1 processing. It can re-call and trim one trace without a reference, or analyze one trace against one short reference FASTA. Both paths re-call bases from analyzed A/C/G/T channels at ABIF PLOC loci, annotate rolling signal-to-noise features and candidate-noisy regions, and score/trim poor read ends; reference analysis additionally aligns either strand and reports normalized primary-sequence SNVs and small indels.

## Status

The JSON-only MVP pipeline is implemented. Its output is an auditable research analysis record, not a diagnostic report. Real-trace release validation requires approved, provenanced AB1 evidence as described in [`docs/data.md`](docs/data.md).

## Run

```bash
cargo run --release -- basecall sample.ab1
cargo run --release -- analyze sample.ab1 \
  --reference references/rCRS.fasta
```

Signal reads `SIGNAL_CONFIG` or `config/signal.toml`. `basecall` atomically writes `results/sample.basecalls.json`; `analyze` atomically writes `results/sample.json`. Each command appends concise stage records to `logs/sample.log`. Records include aggregate counts, thresholds, timings, warnings, and stage-aware failures, but never sequences, per-call peak arrays, or JSON bodies. `SIGNAL_LOG_DIR` can select another log directory. Existing results are never overwritten; per-trace logs are append-only. The binary does not parse `.env`.

For local corpus orchestration, `uv run python scripts/analyze_samples.py` reads the first 89 IDs from `data/MS_010426_001.txt`, preflights the complete selected workload, builds the release binary unless `--no-build` is used, then removes only the selected sample result directories and matching selected logs before rerunning every selected trace. Ambiguous matches, identity collisions, and symlinked cleanup targets are rejected before deletion; artifacts for unselected samples are preserved. A later per-trace failure may leave partial new outputs from earlier successful traces. See [`docs/data.md`](docs/data.md); the core Signal CLI remains one-file-per-invocation and never overwrites an existing result.

## Scope

- exactly one canonical analyzed ABIF/AB1 file per invocation;
- reference-free `signal.basecalls/v1` JSON with full primary/ambiguity/retained sequences, trim bounds, merged noisy regions, provenance, and warning counts;
- for `analyze`, exactly one non-empty plain FASTA record, at most 50,000 bases;
- compact `signal.analysis/v5` JSON with provenance hashes/software, call count and trim bounds, merged noisy regions, an alignment summary, normalized variants with concise call mappings, and warning counts;
- explicit linear/circular topology; bundled rCRS defaults to circular;
- configured inclusive biological regions, with a bundled peak floor of 150 and relative-quality eligibility for SNVs and inserted bases;
- primary-sequence SNVs and normalized insertions/deletions up to 50 bp.

Directories, manifests, globs, batch discovery, SCF, VCF/BCF, FM indexing, two-allele decomposition, heteroplasmy fraction, genotype, pathogenicity, consensus, and assembly are outside the MVP.

## Biological interpretation

Signal reports differences between the conservative signal-derived primary sequence and the supplied reference. Its rolling SNR annotation and relative quality score are not Phred-calibrated; candidate-noisy regions do not suppress calls or variants. Vendor PBAS/PCON may be consumed internally but are not emitted in compact v5. A single trace cannot establish zygosity, homoplasmy, low-level heteroplasmy, phase, or clinical significance.

## Development

Create the locked validation environment with `uv sync --locked`. Activation is optional (`source .venv/bin/activate`); the documented commands use `uv run` directly.

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

Start with [`docs/README.md`](docs/README.md), [`docs/pipeline.md`](docs/pipeline.md), [`docs/basecall-output.md`](docs/basecall-output.md), and [`docs/json-output.md`](docs/json-output.md). Every `src/**/*.rs` has an exact manual counterpart under `docs/src/`.
