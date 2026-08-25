# Signal Pipeline

This document describes the shared read-processing stages and the implemented scientific pipeline of `signal analyze`. `signal basecall` stops after the shared quality-control stage and publishes the reference-free contract described in [`basecall-output.md`](basecall-output.md). It is the authoritative description of the current Rust behavior. Every stage,
substep, and formula below is derived from the source under `src/`; where this
document and the source disagree, the source is ground truth and this document
should be corrected.

The scientific pipeline is deterministic: the same required inputs, effective
configuration, command, and Signal version always produce the same result. Each
command creates one JSON document with its command-specific derived suffix. A
separate nondeterministic append-only operational log records aggregate stage
progress and failures without entering the JSON contract.

## Overview

```text
AB1 + TOML ──► decode ──► basecalling ──► signal_processing ──► quality_control
                                                                     ├─► basecalls/v1
FASTA reference ─────────────────────────────────────────────────────┴─► alignment ─► variant_calling ─► analysis/v5
```

Both commands consume exactly one AB1 trace and one strict TOML configuration. `analyze` additionally consumes one single-record FASTA reference and runs alignment and variant calling. `basecall` performs no reference I/O and stops after the three shared scientific read stages. Each
stage consumes the validated output of the previous stage and produces a new
typed result; no stage mutates shared state.

## Inputs

- **Trace:** one regular ABIF/AB1 file, decoded into four A/C/G/T signal
  channels, basecall positions (`PLOC.2`), and optional vendor evidence
  (`PBAS.2`, `PCON.2`). `P2BA.1` is ignored. Vendor base strings retain uppercase
  IUPAC symbols, and PCON accepts the ABIF one-byte byte or char representation.
- **Reference (`analyze` only):** one plain FASTA record of A/C/G/T/N bases, up to 50,000 bases, interpreted as linear or circular per configuration. `basecall` does not accept or load a reference.
- **Configuration:** one strict TOML file selected by `SIGNAL_CONFIG` or
  `config/signal.toml`. Unknown keys, missing sections, and out-of-range values
  are errors.

## Stage 1 — Decode (`signal.abif_decode/v1`)

Parses the ABIF container and validates every directory entry, offset, element
size, and element count before access. It extracts:

- the four `DATA.9`–`DATA.12` channels as signed 16-bit samples, reordered into
  canonical A/C/G/T order using the `FWO_.1` channel-order string;
- the `PLOC.2` basecall positions (strictly increasing, within the sample
  range);
- optional vendor base strings and quality values, each validated to match the
  number of basecall positions.

The decoded chromatogram records the source file name and SHA-256, the canonical
four channel arrays, the basecall positions, and optional vendor evidence. ABIF
version, channel order, and sample count are validated during decode but are not
duplicated as retained metadata.

## Stage 2 — Basecalling (`signal.peak_recall/v2`)

Re-calls every vendor-defined locus from the channel signals. Vendor base
strings are retained as evidence but never replace signal-derived re-calling.

### Substep 2.1 — Call windows

For each basecall position `p[i]`, a half-open sample window is built from the
midpoints of neighboring positions:

- first window: `[p[0] - (p[1]-p[0])/2, midpoint(p[0], p[1]))`;
- interior window `i`: `[midpoint(p[i-1], p[i]), midpoint(p[i], p[i+1]))`;
- last window: `[midpoint(p[n-2], p[n-1]), p[n-1] + (p[n-1]-p[n-2]+1)/2)`,
  clamped to the sample count.

`midpoint(a, b) = a + (b - a) / 2`. At least two basecall positions are
required.

### Substep 2.2 — Per-channel peak selection

Within each window, each channel is searched for a positive local maximum. A
sample `v` at position `j` is a local maximum when
`(v[j-1] <= v && v > v[j+1]) || (v[j-1] < v && v >= v[j+1])`. The highest such
sample is the channel peak. If no positive local maximum exists, the channel
value at the basecall position is used as a fallback. Each channel peak records
its base, height, position, and source (`local_maximum` or `ploc_fallback`).

### Substep 2.3 — Call decision

The four channel peaks are ranked by height (ties broken by channel order
A < C < G < T). Let `top` be the highest height. If `top <= 0` or the second
peak ties `top`, the call is unresolved (`N`). Otherwise:

- **Qualifying channels** are those with positive height and
  `height / top >= secondary_peak_ratio`.
- **Primary** is the strongest base when one to three channels qualify; four qualifying channels produce `N`.
- **Ambiguity** depends on the number of qualifying channels: one base maps to
  itself (canonical); two bases map to the standard two-base IUPAC symbol; three
  bases are unresolved `N` (primary is still the strongest); four bases are
  unresolved `N` for both primary and ambiguity.
The primary and ambiguity sequences are the concatenation of the per-call
primary and ambiguity symbols.

## Stage 3 — Signal processing (`signal.windowed_snr/v1`)

Calculates observation-only signal-quality features from the immutable analyzed channels and basecalling evidence. It uses full-width, stride-one windows of configured size `5..=10` calls. Each base call retains the sample interval used for peak selection, so a rolling call interval maps to one exact channel-sample span.

For each channel, the local baseline is the median sample and noise sigma is the median absolute deviation of first differences divided by `0.67448975 × sqrt(2)`, with a one-channel-unit floor. Selected peak heights are baseline-corrected and divided by channel noise. Every internal window records its minimum primary SNR, maximum secondary SNR, and whether the minimum is strictly below `minimum_primary_snr`. Values are rounded to six decimal places before comparison; compact v5 serializes only each merged region's minimum primary SNR.

Overlapping or adjacent candidate-noisy windows are unioned into 0-based half-open call and sample intervals only when a consecutive run contains at least `minimum_noisy_windows` windows (default 2). Isolated candidate windows do not form a noisy interval. Clean gaps are never filled. Windows remain internal; compact v5 emits only merged regions. These annotations do not alter calls, quality, trimming, alignment, warning totals, or variant eligibility. See [`signal-processing.md`](signal-processing.md) for formulas, evidence, and limitations.

## Stage 4 — Quality control (`signal.apollo_relative_quality/v1`,
`signal.apollo_end_trim/v1`)

Computes one bounded, uncalibrated quality value per call and selects one
retained interval. It never removes internal sequence regions.

### Substep 4.1 — Per-call penalty

For each call `i`, a window of `trim_window_size` calls centered on `i` is
examined. The penalty is the sum of two components:

- **Ambiguity penalty:** the count of calls in the window whose ambiguity symbol
  is not a canonical A/C/G/T.
- **Spacing penalty:** with `mean_spacing` the average distance between adjacent
  basecall positions across the whole read, and `min`/`max` the minimum and
  maximum adjacent spacing inside the window, the spacing penalty is
  `floor((|max - mean| + |min - mean|) / 2)`.

The penalty is `ambiguity + spacing_penalty`.

### Substep 4.2 — Best section

The best contiguous section is the window of length
`max(1, floor(call_count * best_section_fraction))` with the minimum summed
penalty. Its average penalty is recorded.

### Substep 4.3 — Relative quality score

Scores are uncalibrated and bounded. Let `max_penalty` be the largest penalty in
the read. If `max_penalty <= 0`, every call receives
`max_relative_quality_score`. Otherwise each call receives

```text
floor(max_relative_quality_score * (1 - penalty / max_penalty))
```

clamped to `[0, max_relative_quality_score]`. These scores are **not** Phred
calibrated; `phred_calibrated` is always `false`.

### Substep 4.4 — End trimming

The trim threshold is `trim_stringency * best_average * trim_window_size`.
Starting from the best section, the algorithm walks outward and stops when a
window's summed penalty exceeds the threshold, producing `trim_start` and
`trim_end`. The retained interval must contain at least
`minimum_retained_bases` calls, otherwise analysis fails. The retained sequence
is `primary_sequence[trim_start..trim_end]`.

### Substep 4.5 — Per-call record

Each call records its penalty, relative quality score, and optional vendor
quality. `vendor_quality_applies` is true only when a vendor quality exists and
the vendor primary agrees with the signal primary. Retention is represented once
by the global trim interval rather than duplicated per call.

## Stage 5 — Alignment (`signal.gotoh_semiglobal/v1`)

Aligns the retained primary sequence to the reference with affine-gap Gotoh
dynamic programming. Alignment is semi-global: the retained query is fully
consumed while unaligned reference flanks are allowed.

### Substep 5.1 — Orientation candidates

The retained query is aligned in both orientations:

- **forward:** the retained sequence as-is;
- **reverse:** the reverse complement of the retained sequence.

For a circular reference, the reference is duplicated (concatenated with itself)
so the query may wrap across the origin; the working reference length is the
modulo length. A traceback may consume at most one reference length, so a query
whose required reference span is longer than the circle is unsupported.

### Substep 5.2 — Gotoh scoring

Three dynamic-programming matrices track match, insertion, and deletion states.
A substitution scores `match_score` for equal canonical bases, `mismatch_score`
for unequal canonical bases, and `ambiguous_score` when either base is not
canonical. A gap of length `k` costs `gap_open_score + k * gap_extension_score`.
Endpoint candidates are ranked from the last query row, allowing free reference
flanks. For a circular reference, Signal selects the highest-scoring traceback
whose consumed reference span is at most one circle rather than letting an
invalid unbounded candidate mask a valid placement. Allocation is bounded by a
compiled cell cap.

### Substep 5.3 — Traceback

The traceback internally decodes the selected path into equal-length gapped query and
gapped reference strings, an operation-run string (e.g. `5M`, `3M1I1M`), and
alignment metrics. Compact v5 emits only the selected alignment summary and
reference segments, not the rows, operation runs, or score. When multiple paths tie, a documented state order
(match > deletion > insertion) makes the result deterministic. Metrics are:

- `exact_matches`, `mismatches`, `gap_opens`;
- `callable_columns` (columns where both bases are canonical);
- `callable_identity` = `exact_matches / callable_columns` (0 when no callable
  columns);
- `unresolved_query_bases` (query `N` columns).

### Substep 5.4 — Orientation selection

The forward and reverse candidates are compared by score, then exact matches,
then fewer mismatches, then fewer gap opens. The strictly better orientation is
selected; an exact tie is an error. The selected orientation must meet
`minimum_callable_bases` and `minimum_identity`, otherwise analysis fails.

### Substep 5.5 — Reference segments

For a linear reference, the alignment maps to one half-open reference segment.
For a circular reference, the aligned span is projected back onto the reference;
if it crosses the origin it is split into two segments and `wraps_origin` is
`true`.

## Stage 6 — Variant calling (`signal.primary_difference/v3`)

Extracts normalized primary-sequence differences from the selected alignment.
Only differences in the primary sequence are considered; no allele-frequency,
genotype, or heteroplasmy inference is performed.

### Substep 6.1 — Difference extraction

Walking the alignment columns:

- a column where the query is `-` is a **deletion** of the reference bases;
- a column where the reference is `-` is an **insertion** of the query bases;
- a column with unequal canonical query and reference bases is an **SNV**.

Differences whose allele contains a non-canonical base, or whose indel length
exceeds `max_indel_length`, increment the excluded-candidate warning count rather
than being reported.

### Substep 6.2 — Normalization

Reported variants are normalized:

- **linear references:** indels are left-normalized against the reference where
  an equivalent placement exists (`linear_left`). When no aligned left flank
  exists, the actual reference predecessor is derived from the event position; a
  true linear origin insertion/deletion right-anchors to the next reference base.
- **circular references:** indels are placed at the canonical rotation
  (`circular_canonical`). Repeat normalization walks the whole circle, so the
  resulting representation is anchor-independent.

Internally each variant retains its contig, 1-based position, reference/alternate
alleles, kind, normalization, and direct call mappings. Compact v5 emits only
`position`, `reference`, `alternate`, `kind`, and `calls`. Every mapped call keeps
its original 0-based `index`, ABIF `ploc`, trace-strand `primary`/`ambiguity`, and
optional aligned 1-based biological `position`. Supporting calls additionally
emit only `maximum_peak_height` and uncalibrated `relative_quality`; full channel
peaks, penalties, and vendor evidence are omitted. Inserted supporting calls omit
biological position; deletions carry aligned flanks only. The emitted reference
allele is validated against the supplied reference. Normalization may move the
allele representation without changing the observed call mappings.

### Substep 6.3 — Configured eligibility

A normalized candidate is retained only when its 1-based anchor `position` lies
inside at least one configured inclusive region. SNV supporting calls and every
inserted-base supporting call must each have a highest A/C/G/T peak greater than
or equal to `minimum_peak_height` and an uncalibrated relative score strictly
greater than `relative_quality_threshold`. Insertion flanks are not evaluated.
Deletions have no supporting trace base, so their flanks are not subjected to
peak or quality thresholds; their normalized anchor must still be in a region.
Vendor PCON is not used by this filter.

Each removed candidate increments `excluded_variant_candidates` once, even when
it fails more than one eligibility condition. The pure variant stage also returns
a concise exclusion diagnostic containing kind, contig, normalized position when
available, and all failed rules. Pipeline orchestration writes one WARN record per
diagnostic without reference/alternate alleles.

### Substep 6.4 — Ordering

Reported variants are sorted by `(contig, position, reference, alternate)` and
deduplicated.

## Output

The completed `signal.analysis/v5` result contains compact provenance
hashes/software, read count and trim bounds, merged candidate-noisy regions, the
selected alignment summary, normalized variants with concise call mappings and
supporting peak/relative-quality scalars, and warning counts. It omits filenames,
full sequences, individual rolling windows, gapped rows, operation runs, method
constants, full peaks, vendor data, and redundant fields. The strict configuration
remains schema version 4. No compatibility result is emitted. The document is
published atomically to `results/<trace-stem>.json` without overwriting. Operational records are appended
separately to `$SIGNAL_LOG_DIR/<trace-stem>.log` (default `logs/`) and are not part
of deterministic JSON. One run-correlated record summarizes input/decode,
basecalling, signal processing, quality control, alignment, variant calling, and publication
readiness with aggregate metrics and elapsed milliseconds. WARN records identify
removed candidates by kind/contig/position/reasons and summarize final warning
categories; ERROR records identify the active failed stage. Records omit complete
sequences, alleles, region contents, per-call peaks, alignment strings, and JSON
bodies. The JSON shape is defined in
[`json-output.md`](json-output.md), validated by
[`schemas/analysis-v5.schema.json`](schemas/analysis-v5.schema.json), and shown in
[`examples/analysis-v5.example.json`](examples/analysis-v5.example.json).

## Biological limitations

Signal is a primary-sequence analysis tool, not a clinical or population
diagnostic. The following limitations are intentional and documented:

- **No genotype or heteroplasmy calls.** The pipeline reports differences in a
  single primary sequence. It does not estimate allele fractions, genotype
  likelihoods, or heteroplasmy levels, and it does not decompose mixed or
  two-allele signals.
- **Observational SNR.** Rolling SNR values are robust local features, not Phred scores or error probabilities. Candidate-noisy intervals do not suppress calls or variants.
- **Uncalibrated quality.** Quality values are relative, bounded scores derived
  from ambiguity and peak spacing. They are not Phred-calibrated and are not
  error probabilities.
- **Single reference, single orientation.** The query is aligned to one
  reference record in one of two orientations. Multi-contig references,
  alternative references, and reference search/indexing are out of scope.
- **Primary-sequence variants only.** Variants are derived from the conservative
  signal-derived primary sequence. A two-channel ambiguity may still contribute
  its strongest base to a primary-sequence difference, but it is not a genotype or
  heteroplasmy call. Unresolved N differences, indels longer than
  `max_indel_length`, out-of-region candidates, and SNV/insertion candidates
  below configured supporting-signal thresholds are excluded.
- **Sanger trace limitations.** Basecalling depends on the quality of the
  four-channel signal and the vendor-defined basecall positions. Poor signal,
  mixed templates, and sequencing artifacts can produce unresolved (`N`) calls
  or excluded candidates rather than confident differences.
- **No clinical interpretation.** The output is a technical analysis document.
  It does not assign pathogenicity, disease association, or clinical
  significance to any observed difference.
