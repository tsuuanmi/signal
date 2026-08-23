# Signal Software Requirements Specification

## 1. Purpose

Signal is a deterministic Rust CLI for research analysis of one Sanger ABIF/AB1 chromatogram against one short reference. Normative terms **MUST**, **SHOULD**, and **MAY** apply to every `SRS-*` item.

## 2. Inputs and process boundary

- **SRS-IN-001:** One invocation MUST accept exactly one regular non-empty AB1 path and one required regular non-empty FASTA path, then derive exactly one output target. Directories, lists, manifests, globs, and repeated traces MUST NOT be accepted.
- **SRS-IN-002:** AB1 bytes MUST begin with `ABIF`; every directory count, size, product, offset, inline payload, and allocation MUST be checked before use.
- **SRS-IN-003:** Canonical decode MUST require `DATA.9-12`, `FWO_.1`, and `PLOC.2`; FWO MUST be an exact A/C/G/T permutation; channels MUST be equally sized; PLOC MUST be strictly increasing and in range.
- **SRS-IN-004:** `PLOC.2` is required; `PBAS.2` and `PCON.2` MAY be consumed as optional vendor evidence. `P2BA.1` MUST be ignored. Uppercase IUPAC vendor bases and the ABIF one-byte byte/char PCON representations MUST be accepted. No alternate-tag fallback is permitted.
- **SRS-IN-005:** FASTA MUST contain exactly one non-empty A/C/G/T/N record no longer than 50,000 bases.
- **SRS-IN-006:** Empty, missing, malformed, unsupported, over-limit, or unreadable input MUST return a typed error without panic or result file.
- **SRS-IN-010:** The command MUST be `signal analyze <trace.ab1> --reference <reference.fasta>` and derive `results/<trace-stem>.json`; no output-path compatibility option is permitted.
- **SRS-IN-011:** Help/version MUST succeed without reading analysis inputs.
- **SRS-IN-012:** Invalid CLI arguments MUST produce concise stderr and nonzero status.

## 3. Configuration

- **SRS-CFG-001:** Signal MUST load `SIGNAL_CONFIG` or `config/signal.toml`; it MUST NOT parse `.env`.
- **SRS-CFG-002:** Schema version MUST be integer `4`; all documented sections/keys are required.
- **SRS-CFG-003:** Unknown/duplicate keys, missing fields, non-finite values, unsupported enums/versions, and invalid ranges MUST fail.
- **SRS-CFG-004:** Environment MUST NOT override individual scientific settings. `SIGNAL_LOG_DIR` MAY select only the operational log directory.
- **SRS-CFG-005:** JSON MUST include the configuration checksum and versioned method IDs, but not the local config path or full effective-value expansion. Effective values and configuration schema version remain in the selected strict TOML.
- **SRS-CFG-006:** Hard caps MUST bound AB1 bytes, reference length, alignment cells, indel length, and reachable peak thresholds before unsafe allocation.

## 4. Signal-derived base re-calling

- **SRS-BC-001:** Calls MUST derive from analyzed A/C/G/T signals at validated PLOC loci. PBAS MUST NOT become final algorithm output.
- **SRS-BC-002:** Windows MUST use neighboring PLOC midpoints with bounded first/last extrapolation.
- **SRS-BC-003:** Each channel MUST use its strongest positive local maximum under the documented plateau rule, or its PLOC sample with an explicit fallback marker.
- **SRS-BC-004:** No positive strongest signal or exact strongest tie MUST yield primary N.
- **SRS-BC-005:** One qualifying channel MUST call its base canonically; two qualifying channels MUST use the standard two-base IUPAC code on the strongest primary; three qualifying channels MUST retain the strongest primary with unresolved `N` ambiguity; four qualifying channels MUST be unresolved `N` for both primary and ambiguity.
- **SRS-BC-006:** Every call MUST internally retain its original index, PLOC, call-window sample bounds, four peak heights/positions/sources, primary, ambiguity, qualifying channels, and vendor agreement. JSON MUST expose these local peak details only for calls associated with reported variants.
- **SRS-BC-007:** No sample-specific poly-C correction or reference-aware basecall rescue is permitted; configured biological regions apply only after variant normalization.

## 5. Observational signal processing

- **SRS-SIG-001:** Signal processing MUST read the immutable analyzed A/C/G/T channels and basecalling evidence; it MUST NOT replace decoded channels or selected peaks.
- **SRS-SIG-002:** Configuration MUST require a rolling window in `5..=10` bases, a finite positive minimum primary SNR, and a minimum noisy-window run length of at least 2.
- **SRS-SIG-003:** Every emitted window MUST have the complete configured width and stride one, with explicit 0-based half-open call and sample intervals.
- **SRS-SIG-004:** Baseline, first-difference MAD noise, primary SNR, secondary SNR, finite noise flooring, rounding, and threshold comparison MUST follow the documented `signal.windowed_snr/v1` formula.
- **SRS-SIG-005:** Overlapping or adjacent candidate-noisy windows MUST be unioned without bridging clean gaps, and a noisy interval MUST require at least the configured minimum run length.
- **SRS-SIG-006:** Signal annotations MUST NOT alter quality scores, trim bounds, alignment, warning totals, or variant eligibility. They MUST NOT be described as Phred, error probabilities, genotype, or heteroplasmy evidence.
- **SRS-SIG-007:** A read shorter than the configured signal window MUST fail with a typed signal-processing error rather than emit partial windows.

## 6. Quality control

- **SRS-QC-001:** Each call MUST receive a documented ambiguity/spacing penalty and bounded relative score.
- **SRS-QC-002:** The relative score MUST state `phred_calibrated=false`; PCON MUST remain separate and apply only when PBAS agrees with the re-called primary.
- **SRS-QC-003:** A zero maximum penalty MUST produce maximum relative scores without division by zero.
- **SRS-QC-004:** Trimming MUST remove only left/right tails and retain the best section, half-open trim interval, retained sequence, penalty, score, and vendor quality applicability. JSON MUST expose the trim interval/sequence globally and quality details only for variant-associated calls.
- **SRS-QC-005:** Fewer than configured minimum retained bases MUST fail with a typed QC error.

## 7. Alignment

- **SRS-ALN-001:** Signal MUST align retained forward and reverse-complement queries with affine-gap semi-global Gotoh, consuming the complete query and allowing free reference flanks.
- **SRS-ALN-002:** A gap of length `k` MUST score `open + k × extension`; ambiguous/N comparison MUST use its configured score.
- **SRS-ALN-003:** Traceback MUST use the documented deterministic state and gap-extension tie order. On equal scores the state preference is Match > Deletion > Insertion.
- **SRS-ALN-004:** Circular references MUST align against a doubled sequence, consume at most one reference length, canonicalize modulo coordinates, and expose two segments when crossing origin.
- **SRS-ALN-005:** Both orientations MUST be evaluated internally. JSON MUST report only the selected orientation, score, metrics, rows, operation runs, and segments; original-call mapping is exposed through each variant's direct `calls` array.
- **SRS-ALN-006:** A remaining orientation tie, modulo-distinct placement tie, insufficient callable columns, low identity, over-limit matrix, or invalid traceback MUST fail explicitly.

## 8. Primary-sequence differences

- **SRS-VAR-001:** Variants MUST derive only from the selected primary-sequence alignment.
- **SRS-VAR-002:** Canonical primary A/C/G/T mismatches MAY produce SNVs; unresolved primary N differences MUST be excluded and counted. A two-channel ambiguity may still yield a primary-sequence difference from its strongest channel.
- **SRS-VAR-003:** Contiguous gaps MAY produce insertions/deletions no longer than configured changed length, excluding the anchor.
- **SRS-VAR-004:** Linear indels MUST be minimized/left-normalized; circular indels MUST use bounded, anchor-independent canonical rotation. When no aligned left flank exists, the actual reference predecessor MUST be derived; a true linear origin insertion/deletion MUST right-anchor to the next reference base.
- **SRS-VAR-005:** Reported variants MUST include contig, 1-based `position`, ref/alt, kind, normalization, `primary_sequence_difference` classification, and a direct `calls` array.
- **SRS-VAR-006:** Every mapped call MUST preserve its original call `index`, ABIF `ploc`, and aligned biological `position`. Inserted supporting calls MUST omit biological position; deletions MUST contain flanks only and MUST NOT fabricate deleted-base signal/quality. Emitted reference alleles MUST be validated against the supplied reference.
- **SRS-VAR-007:** Indel normalization MUST NOT rewrite observed call/reference mappings; normalized variant position and observed flank positions MAY differ in repeats.
- **SRS-VAR-008:** Variant alleles MUST use the reference strand. Original call bases and A/C/G/T peaks MUST retain the trace strand, including reverse alignments.
- **SRS-VAR-009:** Genotype, zygosity, homoplasmy, heteroplasmy fraction, phase, PHFinder, pathogenicity, and clinical significance are prohibited in Signal output.
- **SRS-VAR-010:** Every reported variant's normalized 1-based anchor position MUST lie in at least one configured inclusive biological region.
- **SRS-VAR-011:** Every SNV supporting call and every inserted-base supporting call MUST meet the configured maximum-channel peak floor and strictly exceed the configured relative-quality threshold. Insertion flanks and deletion flanks MUST NOT be used for this supporting-evidence gate.

## 9. JSON output

- **SRS-OUT-001:** Success MUST create exactly one analysis result at `results/<trace-stem>.json`; VCF/BCF and output-path compatibility options MUST NOT be created. Operational logging MUST remain a separate append-only sidecar.
- **SRS-OUT-002:** JSON MUST validate against Draft 2020-12 `docs/schemas/analysis-v4.schema.json` and identify `signal.analysis/v4`.
- **SRS-OUT-003:** JSON MUST include compact deterministic identities, core sequence/trim information, rolling signal-quality windows and merged candidate-noisy regions, the selected alignment with gapped rows, normalized variants, and warning counts. It MUST omit complete channel arrays and non-variant per-call/intermediate tables.
- **SRS-OUT-004:** Every reported variant call MUST include role, concise mapped coordinates, A/C/G/T peak height/position/source, and relative/vendor quality semantics.
- **SRS-OUT-005:** JSON MUST use concise context-defined coordinate names: biological `position` is 1-based; call `index`, `ploc`, and peak `position` are 0-based; interval `start`/`end` is 0-based half-open.
- **SRS-OUT-006:** Output MUST be fully serialized, flushed, synchronized, and atomically published without overwriting. Failure MUST leave no result.
- **SRS-OUT-007:** Deterministic output MUST omit timestamp, duration, host, random ID, absolute command/config paths, and unordered maps.
- **SRS-OUT-008:** Rust MUST append timestamped, run-correlated INFO/WARN/ERROR stage records to `$SIGNAL_LOG_DIR/<trace-stem>.log` (default `logs/`) without writing operational records to application stdout/stderr. Records MUST cover each processing-stage boundary with concise aggregate metrics and timings, MUST remain one physical line, and MUST omit complete sequences, peak arrays, configured region contents, alleles, operation strings, and JSON bodies.
- **SRS-OUT-009:** Each excluded variant candidate MUST produce a WARN record containing its kind, contig, normalized position when available, and every rejection reason. Removed-variant records MUST omit reference and alternate alleles.

## 10. Compatibility, quality, and validation

- **SRS-COMPAT-001:** Apollo comparisons MUST follow `compatibility.md`; known defects are intentional divergences, not parity failures.
- **SRS-COMPAT-002:** Approved differential evidence MUST compare exact decoded arrays and unaffected deterministic results; normalized variants compare by full tuple without ignoring extras/missing calls.
- **SRS-NFR-001:** Production code MUST forbid unsafe Rust and avoid production `unwrap`/`expect`.
- **SRS-NFR-002:** Scientific stage functions MUST be side-effect-free and return typed results; only pipeline-level operational logging and report publication write files.
- **SRS-NFR-003:** Representative 500–1,000 base release analysis SHOULD complete within 30 seconds and 512 MiB on a documented host.
- **SRS-NFR-004:** Every Rust source MUST have an exact current `docs/src` counterpart.
- **SRS-VAL-001:** Parser, calling, signal processing, QC, alignment, normalization, JSON, and atomic publication MUST have focused boundary/adversarial tests.
- **SRS-VAL-002:** A synthetic canonical ABIF MUST exercise end-to-end forward/reverse and variant behavior without identifying data.
- **SRS-VAL-003:** Real-trace release evidence MUST follow `data.md`; ignored local data MUST never be a build/test prerequisite.
- **SRS-VAL-004:** Format, check, Clippy warnings-denied, all tests, rustdoc, schema/example validation, TOML validation, docs mirror, and rCRS identity gates MUST pass.
