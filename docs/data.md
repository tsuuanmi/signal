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
`data/raw/MS_010426_001/`, use the bundled rCRS/configuration, and write per-trace results under `results/<sample-id>/<trace-stem>.json`. After every trace for a selected sample succeeds, it also writes the compact sample aggregate as `results/<sample-id>/<sample-id>.json`. The persistent batch log is one `logs/<sample-id>.log` per sample. Per-trace helper `analyze` invocations still produce the reviewer-facing trace JSON files, but their operational logs stay inside temporary workspaces; the subsequent `signal sample` run records the authoritative nested trace-stage events in the sample log.

The wrapper performs a clean selected rerun:

1. read and validate the complete selected manifest prefix;
2. discover every selected trace and reject missing matches, ambiguous ownership,
   duplicate selected IDs, unsafe target types, and symlinks;
3. reject output/log roots that overlap each other or any manifest, trace,
   reference, configuration, or binary path, then preflight every selected cleanup
   target;
4. build the release binary unless `--no-build` is supplied, then require a
   regular binary;
5. destructively remove only `results/<selected-sample>/` directories and the
   matching `logs/<selected-sample>.log` files;
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

Compact analysis v7 omits the trace filename, full called sequences, individual rolling
windows, gapped alignment rows, full per-channel peaks, and vendor data. It keeps
input/reference/configuration hashes, reference identity, read/trim and merged
noisy-region summaries, normalized alleles, concise call mappings, and supporting
maximum-peak/relative-quality values. A result can still identify a sample through
its hashes or biological differences, so derived JSON follows the same approval
and redistribution policy as its AB1 source. Append-only logs can contain trace/reference
names, filesystem paths, hashes, aggregate metrics, thresholds, stage errors, and
removed-variant kinds/coordinates/reasons. They omit alleles and raw scientific
payloads but still follow the same policy; `logs/` is ignored.

## Sample evidence output privacy

`signal.sample_evidence/v7` intentionally contains the sample identifier plus each
contributing AB1 basename for reviewer traceability, along with input SHA-256,
trace-integrity and alignment summaries, run-length total/forward/reverse coverage topology, pairwise overlap/admission evidence, sparse differential loci,
normalized variants with factorized read/eligibility/orientation support topology, and concise call mappings. Filenames, hashes, and biological differences can be
identifying, so sample-evidence JSON follows the same approval, storage, retention,
and redistribution policy as its AB1 sources.

Validation JSONL under `validation-results/` contains per-locus profile geometry and reference coordinates. It is a derived biological artifact with the same approval, storage, retention, and redistribution constraints as the source AB1 and must not be committed.

Manifest-driven validation corpus runs use `scripts/run_validation_corpus.py`. Real
manifests should remain under ignored local data such as `data/validation/`, and the
runner publishes only under ignored `validation-results/`. The corpus index deliberately
omits local trace paths, but it retains trace hashes, truth/grouping metadata, and
biological measurement references, so it remains sensitive derived data and must follow
the same approval and redistribution policy.

Joined validation research datasets generated by `scripts/analyze_validation_corpus.py`
remain under ignored `validation-results/research/`. Their locus/observation CSV tables
omit local AB1 paths but retain trace hashes, truth/holdout metadata, acquisition metadata,
and biological signal geometry, so they remain sensitive derived data under the same
approval, retention, and redistribution policy.

Validation audit outputs generated by `scripts/audit_validation_corpus.py` remain under
ignored `validation-results/audit/`. They omit local AB1 paths and raw log text but retain
trace hashes, sample IDs, acquisition metadata, alignment/signal quality metrics, and
locus-level discordance context. They therefore inherit the same sensitive-derived-data
policy.

Validation curation queues generated by `scripts/prepare_validation_curation.py` remain
under ignored `validation-results/curation/`. The immutable queue retains sample IDs,
trace hashes for flagged reads, review reasons, and locus/read audit context. The separate
decisions template may contain reviewer identities, truth-source references, and
human-authored interpretation once edited, so both files inherit the same
sensitive-derived-data policy and must not be committed with real local corpus content.

Repository examples MUST use synthetic sample/read names and synthetic input hashes.
Do not commit a local sample result merely because v7 is compact. Real local outputs
may inform exploratory development, but release/compatibility evidence requires the
approval record described below.

## Reference-free basecall output privacy

`results/<trace-stem>.basecalls.json` contains complete primary, ambiguity, and
retained sequence strings. It is therefore more directly identifying than compact
analysis v7 and follows the same approval, storage, retention, and redistribution
policy as its source AB1. Its operational log records counts and stage metrics but
never sequence strings or JSON bodies.

## Privacy and repository policy

- `data/`, `results`, `logs/`, and `validation-results/` remain listed in `.gitignore`.
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
