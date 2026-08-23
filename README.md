# Signal

Signal is a focused Rust pipeline for deterministic analysis of one Sanger ABIF/AB1 chromatogram against one short reference FASTA. It re-calls bases from analyzed A/C/G/T channels at ABIF PLOC loci, annotates rolling signal-to-noise features and candidate-noisy regions, scores and trims poor read ends, aligns either strand with affine-gap semi-global Gotoh, and reports normalized primary-sequence SNVs and small indels.

## Status

The JSON-only MVP pipeline is implemented. Its output is an auditable research analysis record, not a diagnostic report. Real-trace release validation requires approved, provenanced AB1 evidence as described in [`docs/data.md`](docs/data.md).

## Run

```bash
cargo run --release -- analyze sample.ab1 \
  --reference references/rCRS.fasta
```

Signal reads `SIGNAL_CONFIG` or `config/signal.toml`, atomically writes one new `results/sample.json`, and appends concise stage records to `logs/sample.log`. Records include aggregate counts, thresholds, timings, warnings, and stage-aware failures, but never sequences, per-call peak arrays, or JSON bodies. `SIGNAL_LOG_DIR` can select another log directory. Existing results are never overwritten; per-trace logs are append-only. The binary does not parse `.env`.

For local corpus orchestration, `uv run python scripts/analyze_samples.py` reads the first 89 IDs from `data/MS_010426_001.txt`, writes every matching trace result under `results/<sample-id>/`, and directs the Rust logs to `logs/`. See [`docs/data.md`](docs/data.md); the Signal CLI itself remains one-file-per-invocation.

## Scope

- exactly one canonical analyzed ABIF/AB1 file per invocation;
- exactly one non-empty plain FASTA record, at most 50,000 bases;
- compact `signal.analysis/v4` JSON with rolling signal-quality windows, merged candidate-noisy regions, concise coordinates, and direct per-variant trace calls containing four-channel peaks and quality;
- explicit linear/circular topology; bundled rCRS defaults to circular;
- configured inclusive biological regions, with a bundled peak floor of 150 and relative-quality eligibility for SNVs and inserted bases;
- primary-sequence SNVs and normalized insertions/deletions up to 50 bp.

Directories, manifests, globs, batch discovery, SCF, VCF/BCF, FM indexing, two-allele decomposition, heteroplasmy fraction, genotype, pathogenicity, consensus, and assembly are outside the MVP.

## Biological interpretation

Signal reports differences between the conservative signal-derived primary sequence and the supplied reference. Its rolling SNR annotation and relative quality score are not Phred-calibrated; candidate-noisy regions do not suppress calls or variants. Vendor PCON is retained separately and applies to a re-called base only when that call agrees with PBAS. A single trace cannot establish zygosity, homoplasmy, low-level heteroplasmy, phase, or clinical significance.

## Development

Create the locked validation environment with `uv sync --locked`. Activation is optional (`source .venv/bin/activate`); the documented commands use `uv run` directly.

```bash
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

Start with [`docs/README.md`](docs/README.md), [`docs/pipeline.md`](docs/pipeline.md), and [`docs/json-output.md`](docs/json-output.md). Every `src/**/*.rs` has an exact manual counterpart under `docs/src/`.
