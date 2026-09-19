# Signal Validation Strategy

## Layers

### Structural gates

- exact `src/**/*.rs` ↔ `docs/src/**/*.md` mirror;
- strict TOML parse plus range/relational checks;
- Draft 2020-12 analysis-v6, basecalls-v1, and sample-evidence-v3 schema validation owned by `scripts/validate_result_schemas.py` and CI, not Rust integration code;
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
- SNV, insertion, deletion, N exclusion, mixed-supporting-signal SNV eligibility, length caps, linear/circular normalization, evidence;
- deterministic sample read ordering, sparse differential-locus retention, indexed variant support, deterministic serialization, and atomic no-overwrite publication.

### Integration tests

Tests construct a canonical synthetic ABIF with known `PLOC(i) = 2 + 4i`. They verify deterministic reference-free basecalls-v1 JSON without FASTA I/O, sequence/trim invariants, command coexistence, logs and no-overwrite behavior, plus deterministic compact analysis-v6 JSON, internal rolling-window behavior and merged noisy-region projection, observation-only variant behavior, forward/reverse reference-oriented SNV peak evidence, insertion/deletion call evidence without fabricated deleted-base signal, indel-normalization preservation, circular segments, and public call quality, strict config v4, malformed input, core CLI no-overwrite publication, and absence of compatibility output. Focused Python tests cover sample-v3 schema rejection cases plus batch preflight, ambiguity/collision/symlink rejection, selected-only destructive cleanup, sample aggregate publication, unselected-artifact preservation, and partial-output behavior after a later failure.

### Differential and real-trace validation

An ignored local trace is not a golden. Before use, record approval, source context, trace/reference/config checksums, region/orientation, generating implementation revision, expected calls/trim/alignment/variants, comparison rules, and redistribution status. Exact fields compare exactly; equivalent indels compare after documented normalization. Missing/extra variants never pass by tolerance.

## Biological validation

The rolling SNR feature and relative quality score are not error probabilities. Validation must not call it Phred or infer clinical sensitivity. A behavior-changing signal cleaner must additionally preserve synthetic 10–30% secondary peaks under baseline drift, impulse noise, compressed peaks, homopolymers, and read ends. Low-level heteroplasmy, genotype, pathogenicity, and diagnostic claims require separate methods and studies.

## Performance

Run a release build with a named 500–1,000 base approved or synthetic trace against rCRS. Record host/toolchain, checksums, elapsed time, and peak memory. Target: ≤30 seconds and ≤512 MiB. Resource-cap failures must occur before large allocation.

## Release gate

All normative requirements and automated checks must pass, and at least one approved real AB1 must have complete end-to-end evidence before describing a scientific release as real-trace validated.
