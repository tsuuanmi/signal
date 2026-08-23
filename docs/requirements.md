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
- **SRS-CFG-005:** JSON MUST include the configuration checksum but MUST omit method constants, the local config path, and the effective-value expansion. Effective values and configuration schema version 4 remain in the selected strict TOML.
- **SRS-CFG-006:** Hard caps MUST bound AB1 bytes, reference length, alignment cells, indel length, and reachable peak thresholds before unsafe allocation.

## 4. Signal-derived base re-calling

- **SRS-BC-001:** Calls MUST derive from analyzed A/C/G/T signals at validated PLOC loci. PBAS MUST NOT become final algorithm output.
- **SRS-BC-002:** Windows MUST use neighboring PLOC midpoints with bounded first/last extrapolation.
- **SRS-BC-003:** Each channel MUST use its strongest positive local maximum under the documented plateau rule, or its PLOC sample with an explicit fallback marker.
- **SRS-BC-004:** No positive strongest signal or exact strongest tie MUST yield primary N.
- **SRS-BC-005:** One qualifying channel MUST call its base canonically; two qualifying channels MUST use the standard two-base IUPAC code on the strongest primary; three qualifying channels MUST retain the strongest primary with unresolved `N` ambiguity; four qualifying channels MUST be unresolved `N` for both primary and ambiguity.
- **SRS-BC-006:** Every call MUST internally retain its original index, PLOC, call-window sample bounds, four peak heights/positions/sources, primary, ambiguity, qualifying channels, and vendor agreement. Compact JSON MUST expose only concise mapped call identity/base fields and, for supporting calls, the maximum selected A/C/G/T peak height.
- **SRS-BC-007:** No sample-specific poly-C correction or reference-aware basecall rescue is permitted; configured biological regions apply only after variant normalization.

## 5. Observational signal processing

- **SRS-SIG-001:** Signal processing MUST read the immutable analyzed A/C/G/T channels and basecalling evidence; it MUST NOT replace decoded channels or selected peaks.
- **SRS-SIG-002:** Configuration MUST require a rolling window in `5..=10` bases, a finite positive minimum primary SNR, and a minimum noisy-window run length of at least 2.
- **SRS-SIG-003:** Every internally calculated window MUST have the complete configured width and stride one with explicit 0-based half-open call and sample intervals. Compact JSON MUST emit merged noisy regions only, not individual windows.
- **SRS-SIG-004:** Baseline, first-difference MAD noise, primary SNR, secondary SNR, finite noise flooring, rounding, and threshold comparison MUST follow the documented `signal.windowed_snr/v1` formula.
- **SRS-SIG-005:** Overlapping or adjacent candidate-noisy windows MUST be unioned without bridging clean gaps, and a noisy interval MUST require at least the configured minimum run length.
- **SRS-SIG-006:** Signal annotations MUST NOT alter quality scores, trim bounds, alignment, warning totals, or variant eligibility. They MUST NOT be described as Phred, error probabilities, genotype, or heteroplasmy evidence.
- **SRS-SIG-007:** A read shorter than the configured signal window MUST fail with a typed signal-processing error rather than emit partial windows.

## 6. Quality control

- **SRS-QC-001:** Each call MUST receive a documented ambiguity/spacing penalty and bounded relative score.
- **SRS-QC-002:** The relative score MUST be explicitly uncalibrated. PCON MUST remain separate internally and apply only when PBAS agrees with the re-called primary; compact JSON MUST omit both the calibration flag and vendor evidence.
- **SRS-QC-003:** A zero maximum penalty MUST produce maximum relative scores without division by zero.
- **SRS-QC-004:** Trimming MUST remove only left/right tails and internally retain the best section, half-open trim interval, retained sequence, penalty, score, and vendor quality applicability. Compact JSON MUST expose only the global trim interval and each supporting variant call's uncalibrated relative quality; sequences, penalties, calibration flags, and vendor quality MUST be omitted.
- **SRS-QC-005:** Fewer than configured minimum retained bases MUST fail with a typed QC error.

## 7. Alignment

- **SRS-ALN-001:** Signal MUST align retained forward and reverse-complement queries with affine-gap semi-global Gotoh, consuming the complete query and allowing free reference flanks.
- **SRS-ALN-002:** A gap of length `k` MUST score `open + k × extension`; ambiguous/N comparison MUST use its configured score.
- **SRS-ALN-003:** Traceback MUST use the documented deterministic state and gap-extension tie order. On equal scores the state preference is Match > Deletion > Insertion.
- **SRS-ALN-004:** Circular references MUST align against a doubled sequence, consume at most one reference length, canonicalize modulo coordinates, and expose two segments when crossing origin.
- **SRS-ALN-005:** Both orientations MUST be evaluated internally. JSON MUST report only the selected orientation, callable-base count, callable identity, unresolved-base count, gap-open count, reference segments, and origin-wrap flag. Score, gapped rows, operation runs, traceback columns, and redundant match/mismatch counts MUST be omitted; original-call mapping is exposed through each variant's direct `calls` array.
- **SRS-ALN-006:** A remaining orientation tie, modulo-distinct placement tie, insufficient callable columns, low identity, over-limit matrix, or invalid traceback MUST fail explicitly.

## 8. Primary-sequence differences

- **SRS-VAR-001:** Variants MUST derive only from the selected primary-sequence alignment.
- **SRS-VAR-002:** Canonical primary A/C/G/T mismatches MAY produce SNVs; unresolved primary N differences MUST be excluded and counted. A two-channel ambiguity may still yield a primary-sequence difference from its strongest channel.
- **SRS-VAR-003:** Contiguous gaps MAY produce insertions/deletions no longer than configured changed length, excluding the anchor.
- **SRS-VAR-004:** Linear indels MUST be minimized/left-normalized; circular indels MUST use bounded, anchor-independent canonical rotation. When no aligned left flank exists, the actual reference predecessor MUST be derived; a true linear origin insertion/deletion MUST right-anchor to the next reference base.
- **SRS-VAR-005:** Reported variants MUST be normalized and include only 1-based `position`, reference/alternate alleles, kind, and a direct `calls` array. Contig, classification, and normalization labels MUST NOT be duplicated in compact JSON.
- **SRS-VAR-006:** Every mapped call MUST preserve its role, original call `index`, ABIF `ploc`, trace-strand primary/ambiguity, and aligned biological `position` when one exists. Supporting calls MUST additionally expose only `maximum_peak_height` and uncalibrated `relative_quality`. Inserted supporting calls MUST omit biological position; deletions MUST contain flanks only and MUST NOT fabricate deleted-base signal/quality.
- **SRS-VAR-007:** Indel normalization MUST NOT rewrite observed call/reference mappings; normalized variant position and observed flank positions MAY differ in repeats.
- **SRS-VAR-008:** Variant alleles MUST use the reference strand. Original call primary/ambiguity MUST retain the trace strand, including reverse alignments; the emitted maximum peak height is strand-independent and full A/C/G/T peak objects MUST remain internal.
- **SRS-VAR-009:** Genotype, zygosity, homoplasmy, heteroplasmy fraction, phase, PHFinder, pathogenicity, and clinical significance are prohibited in Signal output.
- **SRS-VAR-010:** Every reported variant's normalized 1-based anchor position MUST lie in at least one configured inclusive biological region.
- **SRS-VAR-011:** Every SNV supporting call and every inserted-base supporting call MUST meet the configured maximum-channel peak floor and strictly exceed the configured relative-quality threshold. Insertion flanks and deletion flanks MUST NOT be used for this supporting-evidence gate.

## 9. JSON output

- **SRS-OUT-001:** A successful core CLI invocation MUST create exactly one analysis result at `results/<trace-stem>.json`; VCF/BCF, legacy JSON, duplicate compatibility output, and output-path compatibility options MUST NOT be created. Operational logging MUST remain a separate append-only sidecar.
- **SRS-OUT-002:** JSON MUST validate against Draft 2020-12 `docs/schemas/analysis-v5.schema.json` and identify `signal.analysis/v5`. Strict configuration MUST remain schema version 4.
- **SRS-OUT-003:** JSON MUST include compact provenance hashes/software, read call count and trim interval, merged candidate-noisy regions, the selected alignment summary, normalized variants with concise mapped calls, and warning counts.
- **SRS-OUT-004:** JSON MUST omit trace filenames, full primary/ambiguity/retained sequences, individual rolling windows, gapped alignment rows, operation runs, alignment score and redundant metrics, method constants, full A/C/G/T peak objects, penalties/calibration flags, vendor data, expanded configuration, variant contig/classification/normalization labels, and redundant warning fields.
- **SRS-OUT-005:** JSON MUST use concise context-defined coordinate names: biological `position` is 1-based; call `index` and `ploc` are 0-based; trim, reference-segment, and noisy-region `start`/`end` are 0-based half-open.
- **SRS-OUT-006:** Core CLI output MUST be fully serialized, flushed, synchronized, and atomically published without overwriting. A failed core analysis MUST leave no JSON result and MUST NOT replace an existing target.
- **SRS-OUT-007:** Deterministic output MUST omit timestamp, duration, host, random ID, local input/config paths, unordered maps, and all compatibility aliases.
- **SRS-OUT-008:** Rust MUST append timestamped, run-correlated INFO/WARN/ERROR stage records to `$SIGNAL_LOG_DIR/<trace-stem>.log` (default `logs/`) without writing operational records to application stdout/stderr. Records MUST cover each processing-stage boundary with concise aggregate metrics and timings, MUST remain one physical line, and MUST omit complete sequences, peak arrays, configured region contents, alleles, operation strings, and JSON bodies.
- **SRS-OUT-009:** Each excluded variant candidate MUST produce a WARN record containing its kind, contig, normalized position when available, and every rejection reason. Removed-variant records MUST omit reference and alternate alleles.

## 10. External clean batch orchestration

- **SRS-BAT-001:** The external batch runner MUST validate the selected manifest prefix, trace directory, reference, configuration, selected trace workload, identities, destinations, and cleanup targets before deleting any artifact.
- **SRS-BAT-002:** Batch preflight MUST reject invalid or duplicate selected IDs, missing selected traces, traces matching multiple selected samples, trace-stem/log collisions, unsafe target types, path escapes, and symlinked traces or cleanup targets.
- **SRS-BAT-003:** Unless `--no-build` is selected, the release build MUST complete successfully before cleanup. In all modes the selected binary MUST be a regular file before cleanup.
- **SRS-BAT-004:** Cleanup MUST destructively remove only selected `results/<sample-id>/` directories and logs matching selected trace stems or selected sample identities. It MUST preserve every unselected result directory and unrelated log.
- **SRS-BAT-005:** After cleanup, each selected trace MUST run through an isolated one-file core CLI invocation and each generated JSON MUST be placed without overwrite. The wrapper MUST NOT weaken the core CLI's no-overwrite semantics.
- **SRS-BAT-006:** Batch cleanup is not an all-workload transaction. A failure after cleanup MAY leave successful new results/logs from earlier traces and MUST NOT claim to restore the removed prior selected artifacts; the final status MUST report failures.

## 11. Compatibility, quality, and validation

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
