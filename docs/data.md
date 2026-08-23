# Local Data and Fixture Policy

## Purpose

The repository workspace may contain a local AB1 corpus under `data/` for
scientific validation. This directory is development data, not part of the
Signal product interface and not a batch-processing input contract.

## Current local layout

```text
data/
├── MS_010426_001.txt
└── raw/
    └── MS_010426_001/
        └── *.ab1
```

The current corpus contains mitochondrial HV-region traces and identifiers. Its
contents can change independently of the repository because `data/` is ignored.
Documentation and CI must not rely on a particular file count or filename.

## One-file execution rule

Each MVP invocation accepts exactly one AB1 file path:

```bash
signal analyze data/raw/MS_010426_001/example.ab1 \
  --reference references/rCRS.fasta
```

A directory, manifest, glob, or list is not accepted by the MVP. Selecting files
from the local corpus is external test orchestration, not behavior of
`signal analyze`.

For the current local corpus, the external wrapper analyzes every trace belonging
to the first 89 non-empty sample IDs by default and groups outputs by sample:

```bash
uv run python scripts/analyze_samples.py
```

The defaults read `data/MS_010426_001.txt`, search
`data/raw/MS_010426_001/`, use the bundled rCRS/configuration, and write
`results/<sample-id>/<trace-stem>.json`. It sets `SIGNAL_LOG_DIR` so the Rust
logger writes directly to `logs/<trace-stem>.log`. Existing result files are
skipped rather than overwritten. Run
`uv run python scripts/analyze_samples.py --help` to change the manifest, trace
directory, reference, configuration, output or log directory, binary, or sample
limit. This wrapper invokes the one-file CLI once per matching AB1; it does not add
batch behavior to Signal itself.

## Analysis output privacy

The compact JSON contains the trace basename, called sequences, rolling
signal-quality windows and candidate-noisy intervals, alignment, variants, and
local peaks/quality for variant-associated calls. It excludes complete channel
arrays and arbitrary ABIF sample, plate, well, instrument, and run free text. A
result can still identify a sample, so derived JSON follows the same approval and
redistribution policy as its AB1 source. Append-only logs can contain trace/reference
names, filesystem paths, hashes, aggregate metrics, thresholds, stage errors, and
removed-variant kinds/coordinates/reasons. They omit alleles and raw scientific
payloads but still follow the same policy; `logs/` is ignored.

## Privacy and repository policy

- `data/`, `results`, and `logs/` remain listed in `.gitignore`.
- Do not force-add AB1 files, manifests, sample identifiers, or derived outputs.
- Do not copy local traces into `tests/fixtures/` without explicit approval.
- Treat filenames and manifests as potentially identifying metadata.
- CI and normal unit tests must work when `data/` is absent.

## Approval record for a real fixture

Before using a local AB1 as validation evidence, record outside the ignored
corpus or in an approved metadata-only document:

1. approval and intended use;
2. source run and instrument context;
3. primer/region and expected orientation;
4. AB1 SHA-256 checksum;
5. reference path and checksum;
6. Signal configuration checksum or exact values;
7. expected stage outputs and how they were established;
8. whether redistribution is permitted.

A fixture without this record may be used for exploratory local debugging but
not for compatibility or release claims.
