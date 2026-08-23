# Signal Compact JSON Output

`signal analyze <trace.ab1> --reference <reference.fasta>` writes one deterministic file named `results/<trace-stem>.json`. The `results/` directory is created when publication begins. The core CLI never overwrites an existing result. After validating a non-empty UTF-8 trace stem, Rust separately appends nondeterministic operational records to `$SIGNAL_LOG_DIR/<trace-stem>.log` (default `logs/`); that sidecar is outside the JSON contract.

The authoritative contract is [`schemas/analysis-v5.schema.json`](schemas/analysis-v5.schema.json); a synthetic example is [`examples/analysis-v5.example.json`](examples/analysis-v5.example.json). Output v5 is intentionally incompatible with earlier result versions, and Signal emits no compatibility document or duplicate legacy fields. The strict scientific configuration remains schema version 4.

## Top-level fields

| Field | Meaning |
|---|---|
| `schema_version` | Always `signal.analysis/v5`. |
| `provenance` | Software version plus input, reference, and configuration identities. |
| `read` | Original call count and the retained 0-based half-open trim interval. |
| `signal_quality` | Merged candidate-noisy call/sample regions only. |
| `alignment` | Selected-orientation alignment summary and reference segments. |
| `variants` | Normalized primary-sequence differences with concise mapped calls. |
| `warnings` | Counts of unresolved primary calls, multi-channel unresolved calls, and excluded variant candidates. |

All objects are closed by the schema. Compact v5 deliberately omits trace filenames, full primary/ambiguity/retained sequences, individual rolling windows, gapped alignment rows, operation runs, alignment score and redundant match counts, method constants, complete A/C/G/T peak objects, vendor PBAS/PCON data, variant contig/classification/normalization labels, warning totals, and duplicated origin-wrap or vendor-disagreement fields.

## Provenance

`provenance` retains the information needed to identify a deterministic run without exposing the trace filename:

- `software_version`;
- input AB1 `sha256`;
- reference `name`, `topology`, and sequence `sha256`;
- `configuration_sha256`.

The local input/configuration paths, expanded configuration, program constants, timestamps, host data, and method identifiers are not serialized. Effective scientific settings remain in the strict configuration selected for the run.

## Read and signal-quality summary

`read.call_count` is the number of decoded PLOC call loci. `read.trim.start` and `read.trim.end` delimit the retained calls as a 0-based half-open interval. No sequence string is emitted.

`signal_quality.noisy_regions` contains only merged candidate-noisy regions. Each region has 0-based half-open `calls` and `samples` intervals plus `minimum_primary_snr`. Full-width stride-one windows are still calculated internally by `signal.windowed_snr/v1`, but v5 does not serialize them. The regions remain observational and do not alter trimming, alignment, warning counts, or variant eligibility.

## Alignment summary

The selected alignment reports:

- `orientation` (`forward` or `reverse`);
- `callable_bases` and callable `identity`;
- `unresolved_bases` and `gap_opens`;
- one or two 0-based half-open `reference_segments`;
- `wraps_origin`.

Gapped query/reference rows, operation runs, score, exact-match/mismatch redundancy, and traceback columns remain internal.

## Variant calls

Each normalized variant contains only `position`, `reference`, `alternate`, `kind`, and direct `calls`. The variant position is 1-based on the supplied reference strand.

Every mapped call keeps `role`, original 0-based call `index`, 0-based ABIF `ploc`, `primary`, and `ambiguity`. A mapped biological `position` is 1-based and is omitted only for inserted supporting calls.

Supporting calls additionally contain:

- `maximum_peak_height`: the maximum selected A/C/G/T channel height used by the configured evidence floor;
- `relative_quality`: the uncalibrated relative score used by the configured strict quality gate.

Full per-channel peak height/position/source objects, penalties, Phred flags, and vendor scores are not emitted. Flanking calls contain mapping context only and do not carry supporting evidence metrics.

### SNVs

An SNV has one or more supporting calls, each with a biological `position` equal to the observed substituted reference position.

### Insertions

An insertion has one supporting call per inserted base without a biological `position`, plus any available flanking calls with their observed aligned positions. The variant `position` is the normalized reference anchor.

### Deletions

A deletion has no trace call for a deleted reference base, so it contains only available flanking calls. Signal does not fabricate deleted-base peak or quality evidence.

For repeat-associated indels, normalization can move the reported variant representation away from the observed alignment gap. Call positions describe observed mappings; the variant position describes the normalized allele representation.

## Coordinate conventions

| Field | Coordinate system |
|---|---|
| variant/call `position` | 1-based biological reference coordinate |
| call `index` | 0-based original ABIF call index |
| call `ploc` | 0-based ABIF channel-sample index |
| trim, segment, noisy-region `start`/`end` | 0-based half-open interval `[start, end)` |

Variant alleles are written on the supplied reference strand. Call `primary` and `ambiguity` retain the original trace strand, including reverse alignments. Neither peak height nor relative quality implies genotype, zygosity, allele fraction, heteroplasmy, or clinical significance.
