# Signal Compact JSON Output

`signal analyze <trace.ab1> --reference <reference.fasta>` writes one deterministic file named `results/<trace-stem>.json`. The `results/` directory is created when publication begins. Existing results are never overwritten.

The authoritative contract is [`schemas/analysis-v3.schema.json`](schemas/analysis-v3.schema.json); a synthetic example is [`examples/analysis-v3.example.json`](examples/analysis-v3.example.json).

## Top-level fields

| Field | Meaning |
|---|---|
| `schema_version` | Always `signal.analysis/v3`. |
| `meta` | Software, input/reference hashes, config hash, and method IDs. |
| `sequence` | Primary, ambiguity, retained sequence, and trim interval. |
| `alignment` | Selected orientation, score, metrics, segments, operations, and gapped rows. |
| `variants` | Normalized primary-sequence differences and their associated trace calls. |
| `warnings` | Compact counts of non-fatal conditions, plus the boolean `reference_origin_wrap` flag for an origin-crossing circular alignment. |

Complete channel arrays, non-variant call tables, losing alignments, and verbose intermediate records are intentionally omitted. All objects are closed by the schema.

## Coordinate conventions

Concise field names are interpreted by context:

| Field | Coordinate system |
|---|---|
| variant `position` | 1-based normalized biological reference coordinate |
| call `position` | 1-based biological reference coordinate of that aligned call |
| call `index` | 0-based index in the original ABIF call list |
| call `ploc` | 0-based ABIF PLOC channel-sample index |
| peak `position` | 0-based ABIF channel-sample index |
| trim/segment `start`, `end` | 0-based half-open interval `[start, end)` |

An inserted supporting call omits `position` because it has no reference base. Every SNV supporting call and every indel flank has `position`.

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

Peak ratios and relative quality do not imply genotype, zygosity, allele fraction, or heteroplasmy.
