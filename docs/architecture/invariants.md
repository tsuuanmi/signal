# System Invariants

These invariants span modules and are intentionally centralized. SRS and module manuals may reference them but should not redefine them.

## Evidence

- **INV-EVID-001:** Decoded analyzed A/C/G/T channel arrays are immutable source evidence after validation.
- **INV-EVID-002:** Derived signal features, corrected waveforms, quality values, alignments, and variants never overwrite the source evidence from which they were derived.
- **INV-EVID-003:** Vendor PBAS/PCON are vendor evidence, not authoritative Signal output.
- **INV-EVID-004:** `LocusEvidence` and `EvidenceProfile` are derived directly from immutable analyzed A/C/G/T channel values and PLOC-defined geometry; primary/ambiguity calls, selected basecall peaks, and qualifying-channel thresholds MUST NOT determine profile membership or weights.
- **INV-EVID-005:** A zero-positive-signal locus has no evidence profile; the system MUST NOT synthesize a uniform or reference-guided profile as a fallback.
- **INV-EVID-006:** Reference placement MAY consume `EvidenceProfile`, but reference context MUST NOT mutate or rewrite upstream locus evidence or base calls.
- **INV-EVID-007:** PLOC validity and optional vendor-series cardinality are distinct evidence dimensions. Valid PLOC loci remain the authoritative current-method event anchors; PBAS/PCON length mismatch cannot add/remove Signal loci and must remain explicit non-fatal integrity evidence.
- **INV-EVID-008:** Exact signed-16-bit clipping and whole-trace event-signal scale observations are evidence only. They cannot mutate channels, calls, trim bounds, alignment, or variants, and an amplitude ratio cannot become an artifact/dye-blob label without a separately specified method.

## Coordinates and identity

- **INV-COORD-001:** Trace sample positions, original call indexes, PLOC values, trim bounds, signal-window bounds, and reference segments are 0-based unless a contract explicitly says otherwise.
- **INV-COORD-002:** Reported biological variant positions are 1-based.
- **INV-COORD-003:** Half-open intervals use `[start, end)`.
- **INV-COORD-004:** Call index, trace-sample position, and biological reference position are different coordinate domains and must not be substituted implicitly.
- **INV-ID-001:** Reverse-strand processing preserves the original trace call identity and PLOC.
- **INV-ID-002:** Variant normalization may change reported allele placement without rewriting the observed trace-call mappings.

## Scientific state

- **INV-BIO-001:** Unresolved evidence is not equivalent to a reference call, absence of variation, or absence of coverage.
- **INV-BIO-002:** A mixed/secondary signal is an observation, not automatically heteroplasmy, genotype, contamination, or mixture.
- **INV-BIO-003:** A single chromatogram produces read-level evidence, not a sample-level biological conclusion.
- **INV-BIO-004:** A derived confidence value is not an error probability or Phred score unless separately calibrated and validated.
- **INV-BIO-005:** A strongest canonical base with more than one co-localized qualifying channel is mixed signal evidence, not an ordinary clean substitution. If it yields a normalized SNV observation, the observation remains preserved but is not clean-report eligible.

## Read placement and sample boundaries

- **INV-READ-001:** Every trace is scientifically processed and placed independently before any cross-read reconciliation.
- **INV-READ-002:** Read orientation and covered reference segments are derived from alignment evidence; filename, amplicon/HV label, primer label, and declared F/R direction do not constrain default placement.
- **INV-READ-003:** Cross-read reconciliation uses normalized reference-coordinate/variant space rather than canonical F/R pairs as exclusive merge keys.
- **INV-READ-004:** A missing canonical partner does not invalidate an otherwise admitted read; optional assay metadata remains provenance or post-mapping QC unless a separately specified method explicitly says otherwise.
- **INV-SAMPLE-001:** A future consensus sequence is a downstream projection, not the authoritative source of sample variants or discordance.
- **INV-SAMPLE-002:** Missing coverage is distinct from reference support. For each read, mapped reference segments define coverage; inside coverage, omission from sparse `locus_differences[]` means canonical reference match, while positions outside coverage remain uncovered.
- **INV-SAMPLE-003:** Sample evidence defines read identity, unique reviewer-facing filename stem, orientation, and post-trim coverage once in a SHA-sorted read registry. Public locus and normalized-variant evidence reference reads by that unique name; internal aggregation MAY use deterministic indexes but MUST NOT expose them as reviewer-facing identifiers.
- **INV-SAMPLE-004:** Duplicate trace content cannot be counted twice within one sample evidence result.
- **INV-SAMPLE-005:** A locus record exists only when at least one covering read is alternate, unresolved, or deleted. Every covering read at that retained locus remains explicit so reference support and its focused quality evidence are not lost.
- **INV-SAMPLE-006:** Normalized variant support preserves configured eligibility, exclusion reasons, and reviewer-facing reference-oriented base/peak/quality evidence; internal call mappings remain authoritative for scientific traceability, and read-level filtering MUST NOT erase a normalized observation.
- **INV-SAMPLE-007:** Pairwise overlap is discovered only after independent read placement from shared reference coordinates. Non-overlapping reads have no edge; missing an overlapping or canonical F/R partner does not invalidate a read.
- **INV-SAMPLE-008:** Pairwise nucleotide agreement uses only coordinates where both reads carry canonical A/C/G/T query bases. Unresolved symbols and deletions remain outside that denominator; gap/indel evidence is never converted into fabricated nucleotide agreement.
- **INV-SAMPLE-009:** Overlap eligibility is downstream evidence for future consensus and cannot rewrite read placement, read-level observations, or variant eligibility.
- **INV-SAMPLE-010:** Sample coverage topology derives only from selected mapped reference segments and counts all independently placed reads. It cannot inherit pairwise overlap eligibility as read rejection, and orientation depth is not equivalent to nucleotide agreement, consensus confidence, or biological strand independence.

## Pipeline

- **INV-PIPE-001:** Scientific stages consume validated output from earlier stages and do not silently re-parse or reinterpret external inputs.
- **INV-PIPE-002:** Reference-aware stages do not alter upstream signal-derived base calls.
- **INV-PIPE-003:** Expected external-input failures are explicit typed failures, not panics or silent fallbacks.
- **INV-PIPE-004:** Identical scientific inputs, configuration, algorithm versions, and supported execution environment produce deterministic scientific output.

## Output and operations

- **INV-OUT-001:** A failed core analysis publishes no scientific result.
- **INV-OUT-002:** Core result publication is atomic and does not overwrite an existing result.
- **INV-OUT-003:** Operational logs are separate from deterministic scientific result contracts.
- **INV-OUT-004:** A versioned public schema is not mutated retroactively; incompatible contract changes require a new schema version.

## Rust implementation

- **INV-RUST-001:** First-party production code forbids unsafe Rust and denies deprecated API use; first-party source cannot suppress that diagnostic under the source-policy gate.
- **INV-RUST-002:** Production paths do not use `unwrap` or `expect` for recoverable external conditions.
- **INV-RUST-003:** Types and module boundaries should encode coordinate, topology, strand, and validated-state distinctions when doing so removes a concrete failure mode.
- **INV-RUST-004:** Production source must not hide obsolete code behind deprecated declarations, legacy/backward-compatibility feature paths, compatibility-named declarations, or warning suppressions for deprecated/dead/unreachable/unused code; CI enforces this explicit-source policy in addition to compiler and Clippy diagnostics.
