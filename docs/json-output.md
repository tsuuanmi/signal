# Signal Compact JSON Output

`signal analyze <trace.ab1> --reference <reference.fasta>` writes one deterministic file named `results/<trace-stem>.json`. The `results/` directory is created when publication begins. Existing results are never overwritten. After validating a non-empty UTF-8 trace stem, Rust separately appends nondeterministic, run-correlated operational records to `$SIGNAL_LOG_DIR/<trace-stem>.log` (default `logs/`); that sidecar is outside this JSON contract. A refused rerun therefore appends a stage-aware failure record while leaving the existing JSON byte-for-byte unchanged. Clap errors and invalid trace stems occur before logger creation.

The authoritative contract is [`schemas/analysis-v4.schema.json`](schemas/analysis-v4.schema.json); a synthetic example is [`examples/analysis-v4.example.json`](examples/analysis-v4.example.json).

## Top-level fields

| Field | Meaning |
|---|---|
| `schema_version` | Always `signal.analysis/v4`. |
| `meta` | Software, input/reference hashes, config hash, and method IDs. |
| `sequence` | Primary, ambiguity, retained sequence, and trim interval. |
| `signal` | Full rolling SNR windows and merged candidate-noisy call/sample intervals. |
| `alignment` | Selected orientation, score, metrics, segments, operations, and gapped rows. |
| `variants` | Normalized primary-sequence differences and their associated trace calls. |
| `warnings` | Compact counts of non-fatal conditions, including excluded variant candidates, plus the boolean `reference_origin_wrap` flag for an origin-crossing circular alignment. |

Complete channel arrays, non-signal per-call tables, losing alignments, and verbose intermediate records are intentionally omitted. Signal windows are bounded by call count and are observation-only. All objects are closed by the schema.

## Coordinate conventions

Concise field names are interpreted by context:

| Field | Coordinate system |
|---|---|
| variant `position` | 1-based normalized biological reference coordinate |
| call `position` | 1-based biological reference coordinate of that aligned call |
| call `index` | 0-based index in the original ABIF call list |
| call `ploc` | 0-based ABIF PLOC channel-sample index |
| peak `position` | 0-based ABIF channel-sample index |
| signal window/region `calls.start`, `calls.end` | 0-based half-open original call-index interval |
| signal window/region `samples.start`, `samples.end` | 0-based half-open channel-sample interval |
| trim/segment `start`, `end` | 0-based half-open interval `[start, end)` |

An inserted supporting call omits `position` because it has no reference base. Every SNV supporting call and every indel flank has `position`.

## Signal annotations

Each full-width, stride-one window reports `minimum_primary_snr`, `maximum_secondary_snr`, and `candidate_noisy` with call/sample intervals. `noisy_regions` unions overlapping or adjacent candidate windows only when the run contains at least the configured `minimum_noisy_windows` (default 2), and records each region's minimum primary SNR. A region is a window-union approximation, not a per-call classification. These estimated values are finite, non-negative, rounded to six decimal places, and not Phred-calibrated.

The annotation is independent of trimming and variant eligibility. A variant call index may lie inside a candidate-noisy region and still be reported when it passes the existing configured variant rules.

## Variant calls

Each variant contains a direct `calls` array; there is no `evidence` wrapper. Every call includes its role, coordinate mapping, recalled bases, A/C/G/T peaks, and quality.

### SNVs

An SNV has one or more `supporting` calls. The call `position` equals the substituted biological position. `index` identifies the original trace call, and `ploc` identifies that call's ABIF sample locus.

### Insertions

An insertion has:

- one `supporting` call per inserted base, with `index` and `ploc` but no biological `position`;
- available `flanking` calls, each with its actual aligned biological `position`.

The reported variant `position` is the normalized reference anchor. Inserted calls cannot be assigned a reference coordinate without inventing one.

### Deletions

A deletion has no trace call for a deleted reference base. Signal therefore reports only available `flanking` calls. Their positions bound the gap selected by the alignment; no deleted-base peak or quality is fabricated.

For repeat-associated indels, left/circular normalization can move the reported variant representation away from the originally observed alignment gap. Call `position` always describes the observed alignment mapping, while variant `position` describes the normalized allele representation.

## Why channel peak positions differ

`ploc` is the shared ABIF locus for a call. Signal searches each A/C/G/T channel independently inside that call's window and records its strongest local maximum. Dye mobility, peak shape, overlap, and noise can place those four maxima at slightly different sample indexes. Therefore the four peak `position` values are not expected to equal one another or `ploc`.

When a channel has no positive local maximum, Signal uses its value at `ploc` and marks the peak source `ploc_fallback`.

## Strand semantics

Variant `reference` and `alternate` are always written on the supplied reference strand. Call `primary`, `ambiguity`, and A/C/G/T peaks remain in the original trace strand. For a reverse alignment, a supporting trace base is therefore the complement of the variant alternate.

## Quality

Each variant-associated call contains:

- `relative_score` and its `penalty`;
- `phred_calibrated: false`;
- optional vendor `vendor_score` and `vendor_score_applies`.

Peak ratios and relative quality do not imply genotype, zygosity, allele fraction, or heteroplasmy. Variant eligibility uses this uncalibrated `relative_score`, not optional vendor quality: SNV and inserted-base supporting calls must each exceed the configured relative threshold and meet the configured maximum-channel peak floor. Deletion flanks are exempt because they do not measure a deleted base.
