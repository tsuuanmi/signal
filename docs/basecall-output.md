# Signal Reference-Free Basecall Output

`signal basecall <trace.ab1>` reads the strict configuration selected by
`SIGNAL_CONFIG` or `config/signal.toml`, runs canonical ABIF decode, signal-derived
base re-calling, observational signal analysis, and relative quality trimming,
then atomically creates `results/<trace-stem>.basecalls.json`. It does not load a
reference, align, or call variants. Existing targets are never overwritten.

The authoritative contract is
[`schemas/basecalls-v1.schema.json`](schemas/basecalls-v1.schema.json); a synthetic
example is [`examples/basecalls-v1.example.json`](examples/basecalls-v1.example.json).
Every object is closed and `schema_version` is `signal.basecalls/v1`.

## Fields

- `provenance`: software version, input AB1 SHA-256, and complete strict
  configuration SHA-256. The trace filename, local paths, timestamps, and host
  data are omitted.
- `read.call_count`: number of decoded PLOC call loci.
- `read.primary`: strongest conservative signal-derived base at each locus.
- `read.ambiguity`: canonical/IUPAC ambiguity symbol at each locus.
- `read.retained`: the primary sequence inside `read.trim` after end trimming.
- `read.trim`: 0-based half-open call interval `[start, end)`.
- `signal_quality.noisy_regions`: merged observation-only call/sample intervals
  and their minimum primary SNR. Individual rolling windows are omitted.
- `warnings`: unresolved-primary and multi-channel-unresolved counts, plus vendor
  disagreement count when optional vendor calls are available.

The primary and ambiguity sequence lengths equal `call_count`; trim bounds lie
within that count; and `retained` equals the primary sequence slice selected by
the trim interval. These cross-field invariants are enforced by typed Rust
construction and integration tests because JSON Schema cannot express them all.

## Interpretation and privacy

The result contains complete sequence strings and can identify a sample. It must
follow the same approval, storage, and redistribution policy as its source AB1.
The relative score used during trimming and the rolling SNR method are not
Phred-calibrated error probabilities. This output makes no genotype,
heteroplasmy, phase, pathogenicity, or clinical claim.

Operational records append to `$SIGNAL_LOG_DIR/<trace-stem>.log` (default
`logs/`). They include stage metrics, timings, warning counts, and failures, but
never sequence strings, peak arrays, or JSON bodies.
