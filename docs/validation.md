# Signal Validation Strategy

## Layers

### Structural gates

- exact `src/**/*.rs` ↔ `docs/src/**/*.md` mirror;
- strict TOML parse plus range/relational checks;
- Draft 2020-12 schema validation owned by `scripts/validate_analysis_schema.py` and CI, not Rust integration code;
- Markdown links, rustdoc, rCRS source checksum/length, `.env` policy;
- no repository backups or accidental patient/sample fixtures.

### Unit tests

- checked endian/slice/offset arithmetic and ABIF directory/tag layouts;
- FWO permutation, channel cardinality, PLOC ordering/bounds, vendor lengths;
- FASTA records/symbols/length;
- midpoint windows, plateau peaks, PLOC fallback, ties, ambiguity ratios/IUPAC;
- signal baseline/first-difference MAD, noise floor, full rolling windows, thresholds, and merged regions;
- penalty windows, zero-penalty scoring, trim bounds/minimum length;
- Gotoh initialization, free flanks, affine convention, state ties, memory cap, traceback;
- forward/reverse mapping, circular origin, ambiguous placement/orientation;
- SNV, insertion, deletion, N exclusion, length caps, linear/circular normalization, evidence;
- deterministic serialization and atomic no-overwrite publication.

### Integration tests

Tests construct a canonical synthetic ABIF with known `PLOC(i) = 2 + 4i`. They verify deterministic compact JSON, rolling signal windows, candidate-noisy interval merging, observation-only variant behavior, exact forward/reverse SNV call-to-position/PLOC mapping, insertion calls without invented reference positions, deletion flanks without invented peaks, indel-normalization mapping preservation, circular segments, four peaks and quality, strict config, malformed input, no-overwrite publication, and no VCF.

### Differential and real-trace validation

An ignored local trace is not a golden. Before use, record approval, source context, trace/reference/config checksums, region/orientation, generating implementation revision, expected calls/trim/alignment/variants, comparison rules, and redistribution status. Exact fields compare exactly; equivalent indels compare after documented normalization. Missing/extra variants never pass by tolerance.

## Biological validation

The rolling SNR feature and relative quality score are not error probabilities. Validation must not call it Phred or infer clinical sensitivity. A behavior-changing signal cleaner must additionally preserve synthetic 10–30% secondary peaks under baseline drift, impulse noise, compressed peaks, homopolymers, and read ends. Low-level heteroplasmy, genotype, pathogenicity, and diagnostic claims require separate methods and studies.

## Performance

Run a release build with a named 500–1,000 base approved or synthetic trace against rCRS. Record host/toolchain, checksums, elapsed time, and peak memory. Target: ≤30 seconds and ≤512 MiB. Resource-cap failures must occur before large allocation.

## Release gate

All SRS implementation requirements and automated checks must pass, and at least one approved real AB1 must have complete end-to-end evidence before describing a scientific release as real-trace validated.
