# Signal Validation Strategy

## Layers

### Structural gates

- exact `src/**/*.rs` ↔ `docs/src/**/*.md` mirror;
- strict TOML parse plus range/relational checks;
- Draft 2020-12 analysis-v7, basecalls-v2, and sample-evidence-v7 schema validation owned by `scripts/validate_result_schemas.py` and CI, not Rust integration code;
- Markdown links, rustdoc, rCRS source checksum/length, `.env` policy;
- no repository backups or accidental patient/sample fixtures.

### Unit tests

- checked endian/slice/offset arithmetic and ABIF directory/tag layouts;
- FWO permutation, channel cardinality, PLOC ordering/bounds, non-fatal vendor/PLOC cardinality mismatch evidence, PLOC spacing summaries, exact signed-16-bit clipping counts, and event-signal ratio summaries;
- FASTA records/symbols/length;
- midpoint windows, plateau peaks, PLOC fallback, ties, ambiguity ratios/IUPAC;
- shared PLOC locus geometry; basecall-independent nearest-total-event refinement with stronger-neighbor rejection, equal-distance deterministic ties, and PLOC fallback; zero-signal profile absence; threshold-independent A/C/G/T profile mass; signal baseline/first-difference MAD, noise floor, full rolling windows, thresholds, and merged regions;
- penalty windows, zero-penalty scoring, trim bounds/minimum length;
- fixed-point profile substitution quantization, one-hot compatibility with the prior score ordering, missing-profile ambiguous scoring, unresolved primary characters with usable profile evidence, reverse profile complementation, Gotoh initialization, free flanks, affine convention, state ties, memory cap, traceback, score-verified homopolymer/tandem-repeat right canonicalization, profile-sensitive insertion non-shifting, genuine non-indel placement ambiguity, and circular-origin seam protection;
- forward/reverse mapping, circular origin, ambiguous placement/orientation;
- SNV, insertion, deletion, N exclusion, mixed-supporting-signal SNV eligibility, length caps, canonical alignment-anchor preservation for linear/circular indels, and evidence;
- deterministic sample read ordering; run-length total/forward/reverse coverage topology including tiled and origin-spanning segments; Tracy-derived pairwise overlap discovery/admission including non-overlap, minimum comparable-base count, agreement threshold, and unresolved/gap denominator behavior; sparse differential-locus retention with exact total/orientation/state support-topology consistency plus profile-bearing total/forward/reverse subset invariants and structural nucleotide-contribution states covering noisy-profile eligibility, unresolved-profile eligibility, missing-profile exclusion, and deletion-event separation; unit-mass eligible-profile accumulation with exact total/forward/reverse support fixtures, arithmetic mean-profile derivation for non-empty partitions; exact within/between/total heterogeneity fixtures distinguishing replicated mixture from inter-read disagreement; Total Variation orientation-distance bounds/presence rules; and zero contribution/absence for missing-profile/deletion states; reference-oriented basecall-independent profile retention with reverse complementation and no missing-profile fallback; call-backed local noisy-region membership with deletion absence; unified reference-oriented corrected-amplitude/SNR/profile projection including reverse-channel reordering; named-read variant support plus exact read/eligibility/orientation topology consistency; mixed-SNV eligibility retention; deterministic serialization; and atomic no-overwrite publication.

### Integration tests

Tests construct a canonical synthetic ABIF with known `PLOC(i) = 2 + 4i`. They verify deterministic reference-free basecalls-v2 JSON without FASTA I/O, sequence/trim invariants, command coexistence, logs and no-overwrite behavior, plus deterministic compact analysis-v7 JSON, internal rolling-window behavior and merged noisy-region projection, profile-aware forward/reverse placement, reference-oriented SNV peak evidence, insertion/deletion call evidence without fabricated deleted-base signal, indel-normalization preservation, circular profile alignment segments, and public primary-sequence alignment metrics/call quality, strict config v5, malformed input, core CLI no-overwrite publication, and absence of compatibility output. Focused Python tests cover sample-v7 integrity/overlap/schema rejection cases plus batch preflight, ambiguity/symlink rejection, selected-only destructive cleanup, temporary helper trace logging, sample-only persistent logging, sample aggregate publication, unselected-artifact preservation, and partial-output behavior after a later failure. Dedicated Rust validation integration tests require all-reference covered loci to appear in `signal.validation_locus/v2`, require nested call/PLOC/primary-peak/event/profile diagnostics for call-backed observations, keep production `results/` untouched, and enforce atomic no-overwrite measurement publication.

### Differential and real-trace validation

An ignored local trace is not a golden. Before use, record approval, source context, trace/reference/config checksums, region/orientation, generating implementation revision, expected calls/trim/alignment/variants, comparison rules, and redistribution status. Exact fields compare exactly; equivalent indels compare after documented normalization. Missing/extra variants never pass by tolerance.

## Biological validation

`LocusEvidence` and `EvidenceProfile` are observation-only signal representations, not allele fractions or genotype probabilities. The rolling SNR feature and relative quality score are not error probabilities. Validation must not call it Phred or infer clinical sensitivity. A behavior-changing signal cleaner must additionally preserve synthetic 10–30% secondary peaks under baseline drift, impulse noise, compressed peaks, homopolymers, and read ends. Low-level heteroplasmy, genotype, pathogenicity, and diagnostic claims require separate methods and studies.

## Profile-geometry threshold research

Production profile geometry remains threshold-free. Empirical threshold research uses the dedicated `signal-validation` binary so clean reference-matching loci are measured as well as differential loci without changing `signal.sample_evidence/v7`.

A local export runs the same trace/read/sample science path and publishes one deterministic JSON object per covered reference locus to `validation-results/<sample-id>.jsonl`:

```bash
SIGNAL_CONFIG=config/signal.toml \
  cargo run --release --bin signal-validation -- \
  validation-001 trace-a.ab1 trace-b.ab1 \
  --reference references/rCRS.fasta
```

Real validation exports are identifying scientific derivatives and remain ignored local artifacts. A completed corpus can be converted into deterministic joined research tables with:

```bash
uv run python scripts/analyze_validation_corpus.py \
  --corpus-dir validation-results/corpus \
  --output-dir validation-results/research/baseline
```

This preparation step revalidates corpus/measurement provenance, streams joined locus and
read-observation rows to CSV, and reports descriptive nearest-rank geometry percentiles.
It does not choose a threshold or inspect holdout data to tune a rule.

A completed research dataset can then be audited with:

```bash
uv run python scripts/audit_validation_corpus.py \
  --corpus-dir validation-results/full-20260919 \
  --research-dir validation-results/research/full-20260919 \
  --output-dir validation-results/audit/full-20260919
```

The audit publishes read/locus/case review strata only. Corpus-relative outlier flags and
retained-edge discordance context MUST NOT be treated as truth, automatic exclusion, or a
production QC gate.

A completed audit can then be converted into an immutable human-review queue with:

```bash
uv run python scripts/prepare_validation_curation.py \
  --audit-dir validation-results/audit/full-20260919 \
  --output-dir validation-results/curation/full-20260919
```

The generated queue contains mixed loci and flagged reads only. Reviewer decisions are
kept in a separate editable template and are not written back into generated evidence or
the validation manifest automatically.

Threshold development must follow `docs/research/Signal/validation-corpus.md` and `docs/research/Signal/threshold-research.md`: truth provenance, grouped development/holdout separation, repeatability/reproducibility, artifact challenges, false-positive objectives, and operating-domain limitations are required before promotion. Unexpected extreme basecall/profile disagreements must first be characterized with the v2 event-placement diagnostics described in `docs/research/Signal/event-position-diagnostics.md` rather than absorbed into a fitted threshold. Point-mixture and length/indel studies remain separate.

## Performance

Run a release build with a named 500–1,000 base approved or synthetic trace against rCRS. Record host/toolchain, checksums, elapsed time, and peak memory. Target: ≤30 seconds and ≤512 MiB. Resource-cap failures must occur before large allocation.

## Release gate

All normative requirements and automated checks must pass, including the Rust source-policy gate that rejects explicit obsolete/compatibility scaffolding and hidden dead/unused/deprecated production paths. At least one approved real AB1 must have complete end-to-end evidence before describing a scientific release as real-trace validated.
