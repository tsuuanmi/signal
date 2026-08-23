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
logger writes directly to `logs/<trace-stem>.log`.

The wrapper performs a clean selected rerun:

1. read and validate the complete selected manifest prefix;
2. discover every selected trace and reject missing matches, ambiguous ownership,
   duplicate selected IDs, trace-stem/log collisions, unsafe target types, and
   symlinks;
3. reject output/log roots that overlap each other or any manifest, trace,
   reference, configuration, or binary path, then preflight every selected cleanup
   target;
4. build the release binary unless `--no-build` is supplied, then require a
   regular binary;
5. destructively remove only `results/<selected-sample>/` directories and logs
   matching selected trace stems/sample identities;
6. run each selected trace through the one-file CLI and atomically place each new
   result without overwrite, synchronizing both the result directory and every
   parent that gained a newly created directory entry.

Cleanup never removes unselected sample directories or unrelated logs. It occurs
only after successful preflight and build, but it is not transactional across the
whole workload: if a later analysis fails, earlier new results/logs may remain and
the removed prior selected artifacts are not restored. The core CLI itself keeps
its no-overwrite and failure-without-result semantics.

Run `uv run python scripts/analyze_samples.py --help` to change the manifest,
trace directory, reference, configuration, output or log directory, binary, or
sample limit. This wrapper remains external orchestration; it does not add batch
input behavior to `signal analyze`.

## Analysis output privacy

Compact v5 omits the trace filename, full called sequences, individual rolling
windows, gapped alignment rows, full per-channel peaks, and vendor data. It keeps
input/reference/configuration hashes, reference identity, read/trim and merged
noisy-region summaries, normalized alleles, concise call mappings, and supporting
maximum-peak/relative-quality values. A result can still identify a sample through
its hashes or biological differences, so derived JSON follows the same approval
and redistribution policy as its AB1 source. Append-only logs can contain trace/reference
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
