# System Invariants

These invariants span modules and are intentionally centralized. SRS and module manuals may reference them but should not redefine them.

## Evidence

- **INV-EVID-001:** Decoded analyzed A/C/G/T channel arrays are immutable source evidence after validation.
- **INV-EVID-002:** Derived signal features, corrected waveforms, quality values, alignments, and variants never overwrite the source evidence from which they were derived.
- **INV-EVID-003:** Vendor PBAS/PCON are vendor evidence, not authoritative Signal output.

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

## Read placement and sample boundaries

- **INV-READ-001:** Every trace is scientifically processed and placed independently before any cross-read reconciliation.
- **INV-READ-002:** Read orientation and covered reference segments are derived from alignment evidence; filename, amplicon/HV label, primer label, and declared F/R direction do not constrain default placement.
- **INV-READ-003:** Cross-read reconciliation uses normalized reference-coordinate/event space rather than canonical F/R pairs as exclusive merge keys.
- **INV-READ-004:** A missing canonical partner does not invalidate an otherwise admitted read; optional assay metadata remains provenance or post-mapping QC unless a separately specified method explicitly says otherwise.
- **INV-SAMPLE-001:** A future consensus sequence is a downstream projection, not the authoritative source of sample variants or discordance.

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

- **INV-RUST-001:** First-party production code forbids unsafe Rust.
- **INV-RUST-002:** Production paths do not use `unwrap` or `expect` for recoverable external conditions.
- **INV-RUST-003:** Types and module boundaries should encode coordinate, topology, strand, and validated-state distinctions when doing so removes a concrete failure mode.
