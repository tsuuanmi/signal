# Signal Architecture

## Principles

- One AB1, one strict config, one command-specific JSON result, and one run-correlated append history in the per-trace operational log per invocation; reference analysis additionally requires one FASTA.
- Untrusted binary input is checked before every slice, conversion, and allocation.
- Models enforce cardinality and coordinate invariants; scientific functions have no filesystem side effects.
- The CLI and operating-system boundary remain thin.
- Algorithms are deterministic and biologically explicit; known Apollo defects are not compatibility requirements.
- Every Rust source has a same-path manual under `docs/src/`.

## Flow

```text
CLI -> pipeline -> input (strict config + ABIF)
                    |
                    v
                 shared read path
                 basecalling -> signal_processing -> quality_control
                    |                                  |
                    |                                  +-> basecall report v1
                    v
                 analyze only: reference -> alignment -> variant_calling
                                                   |
                                                   +-> analysis report v5

Both reports -> one serializer -> atomic no-overwrite publication
Both commands -> append-only per-trace operational log
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
| `signal_processing` | rolling sample-domain SNR features and merged candidate-noisy regions | channel mutation, calibrated quality, and variant eligibility |
| `quality_control` | penalties, relative scores, end trimming | Phred calibration and variant filtering |
| `alignment` | bounded Gotoh, traceback, orientation, circular projection | variant extraction |
| `variant_calling` | SNV/indel extraction, call/reference mapping, normalization, configured region/supporting-evidence filters | genotype and clinical interpretation |
| `report` | analysis-v5/basecalls-v1 assembly, shared signal projection/serialization, concise mapped-call projection, atomic publish | scientific decisions and compatibility output |
| `pipeline` | command-specific sequencing plus one shared reference-independent read path | algorithm internals |

Dependencies point toward `model`, `config`, and `error`; cycles are forbidden. `signal_processing` reads `Chromatogram` and `BaseCalls` but no algorithm module depends back on it.

## Coordinates and strand

Trace samples, rolling signal-window call indexes, and original call indexes are 0-based. Internal reference intervals are 0-based half-open. Variant positions are 1-based. Reverse alignments retain an explicit oriented-query to original-call mapping. Circular alignments may contain two reference segments when they cross the origin.

## Output projection and transaction

Compact `signal.analysis/v5` projects completed internal models to provenance, read/trim, merged noisy regions, alignment, normalized variants, and warning summaries while omitting full sequences and bulk evidence. `signal.basecalls/v1` projects the shared reference-independent stages to provenance, full primary/ambiguity/retained sequences, trim, merged noisy regions, and warnings without reference, alignment, or variants. Configuration remains schema version 4, and no compatibility result is assembled.

The completed typed result is serialized before filesystem publication. The core CLI writes a sibling temporary file, flushes and synchronizes it, creates the final path without overwrite, removes the temporary link, and synchronizes the directory. A failed core invocation leaves no command result and never replaces an existing file. Operational logs are deliberately separate, timestamped, run-correlated, escaped to one physical line, and append-only. Pipeline orchestration records aggregate metrics and elapsed time at every stage boundary, each removed variant's kind/position/reasons without alleles, the final warning categories, and stage-aware terminal failures. Mandatory pre-publication records are synchronized before the result transaction begins; no required record is written after a successful publication.

## External batch orchestration

`scripts/analyze_samples.py` is outside the core CLI boundary. It validates the manifest, selected traces, identities, destinations, and cleanup targets; rejects ambiguous matches, trace-stem collisions, and symlinks; then builds or validates the binary before deleting anything. Cleanup removes only selected sample directories and matching selected logs, preserving unselected artifacts. Each selected trace still runs through the one-file no-overwrite CLI in isolation. Because cleanup is intentionally destructive and execution is sequential, a later analysis failure may leave partial new outputs from earlier successful traces; it does not restore the removed prior batch.

## Resource bounds

Config/FASTA source files are capped at 1/4 MiB before reading, AB1 input at 64 MiB, normalized references at 50,000 bases, indels at 50 changed bases, and Gotoh traceback at 100 million cells. Checked arithmetic rejects an over-limit job before allocation.
