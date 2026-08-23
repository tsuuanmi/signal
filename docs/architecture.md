# Signal Architecture

## Principles

- One AB1, one reference, one strict config, one JSON result, and one run-correlated append history in the per-trace operational log per invocation.
- Untrusted binary input is checked before every slice, conversion, and allocation.
- Models enforce cardinality and coordinate invariants; scientific functions have no filesystem side effects.
- The CLI and operating-system boundary remain thin.
- Algorithms are deterministic and biologically explicit; known Apollo defects are not compatibility requirements.
- Every Rust source has a same-path manual under `docs/src/`.

## Flow

```text
CLI
 └─ pipeline
     ├─ logger       append-only per-trace operational records
     └─ input
         ├─ config      strict TOML + checksum
         ├─ trace       ABIF directory + DATA/FWO_/PLOC/vendor evidence
         └─ reference   one FASTA + sequence checksum
             ↓
         basecalling    signal-derived calls at PLOC loci
             ↓
         quality_control relative score + end-only trim interval
             ↓
         alignment      forward/reverse semi-global Gotoh, circular-aware
             ↓
         variant_calling normalized, configured-region/signal-filtered differences
             ↓
         report         compact variant-focused JSON + atomic no-overwrite publish
```

The shared `checksum` module provides the stable SHA-256 identities used by
`config`, `trace`, and `reference` loading.

## Boundaries

| Module | Owns | Excludes |
|---|---|---|
| `cli` | command syntax | I/O and algorithms |
| `config` | path resolution, strict parsing, validation, caps | per-value environment overrides |
| `error` | typed cross-stage failures | logging and recovery policy |
| `logger` | append-only timestamped operational records | scientific decisions and JSON output |
| `checksum` | shared stable SHA-256 byte identity | file I/O and policy |
| `model` | validated vocabulary and JSON result records | filesystem and algorithms |
| `trace` | canonical ABIF decode | base calling |
| `reference` | one-record FASTA and identity | alignment |
| `basecalling` | peak windows, peaks, primary/ambiguity calls | trimming and reference knowledge |
| `quality_control` | penalties, relative scores, end trimming | Phred calibration and variant filtering |
| `alignment` | bounded Gotoh, traceback, orientation, circular projection | variant extraction |
| `variant_calling` | SNV/indel extraction, call/reference mapping, normalization, configured region/supporting-evidence filters | genotype and clinical interpretation |
| `report` | compact JSON assembly, mapped-call peak/quality projection, atomic publish | scientific decisions |
| `pipeline` | sequencing the use case | algorithm internals |

Dependencies point toward `model`, `config`, and `error`; cycles are forbidden.

## Coordinates and strand

Trace samples and original call indexes are 0-based. Internal reference intervals are 0-based half-open. Variant positions are 1-based. Reverse alignments retain an explicit oriented-query to original-call mapping. Circular alignments may contain two reference segments when they cross the origin.

## Output transaction

The completed typed result is serialized before filesystem publication. Signal writes a sibling temporary file, flushes and synchronizes it, creates the final path without overwrite, removes the temporary link, and synchronizes the directory. A failed run leaves no analysis result and never replaces an existing file. Operational logs are deliberately separate, timestamped, run-correlated, escaped to one physical line, and append-only. Pipeline orchestration records aggregate metrics and elapsed time at every stage boundary, each removed variant's kind/position/reasons without alleles, the final warning categories, and stage-aware terminal failures. Mandatory pre-publication records are synchronized before the result transaction begins; no required record is written after a successful publication.

## Resource bounds

Config/FASTA source files are capped at 1/4 MiB before reading, AB1 input at 64 MiB, normalized references at 50,000 bases, indels at 50 changed bases, and Gotoh traceback at 100 million cells. Checked arithmetic rejects an over-limit job before allocation.
