# Documentation and Implementation Traceability

This map helps developers and agents move from intent to implementation without duplicating the specification.

| Requirement family | Current method / architecture | Owning implementation | Primary tests / evidence | Public contract |
|---|---|---|---|---|
| `SRS-IN-*` | `pipeline.md`, `architecture.md` | `src/trace/`, `src/reference/`, `src/cli/` | parser/reference/CLI tests, synthetic ABIF | CLI/config contracts |
| `SRS-CFG-*` | `configuration.md` | `src/config/` | strict TOML/config tests | `config/signal.toml` semantics |
| `SRS-BC-*` | `pipeline.md` Stage 2 | `src/basecalling/`, `src/model/basecalls.rs` | basecalling unit tests + approved trace comparison | `signal.basecalls/v2`, mapped calls in analysis |
| `SRS-SIG-*` | `signal-processing.md`, ADR-0028 + ADR-0046 | `src/locus.rs`, `src/model/locus_evidence.rs`, `src/signal_processing/` | locus geometry/profile tests + nearest-event regression + signal feature boundary tests | internal evidence profile + public integrity/noisy-region projections |
| `SRS-QC-*` | `pipeline.md` Stage 4 | `src/quality_control/` | quality/trim unit + real-read review | trim + reviewer-facing `quality` |
| `SRS-ALN-*` | `pipeline.md` Stage 5, ADR-0029 + ADR-0047 + read-observation boundary | `src/alignment/canonical.rs`, `src/alignment/`, `src/model/locus_evidence.rs`, `src/model/alignment.rs`, `src/model/read_observation.rs` | fixed-point profile scoring, one-hot compatibility, unresolved-profile, orientation/traceback/circular tests; score-verified homopolymer/tandem-repeat right-gap and origin-seam fixtures | analysis alignment summary |
| `SRS-SAMPLE-*` | ADR-0023, ADR-0030, ADR-0053, architecture invariants | `src/sample/`, `src/model/sample_evidence.rs`, `src/model/sample_result.rs`, `src/report/sample.rs`, `src/pipeline/sample.rs` | deterministic coverage topology, overlap/admission, differential-locus support topology, public reference-oriented profile/noisy-context projection, structural nucleotide-contribution eligibility, unweighted eligible-profile support aggregation, arithmetic mean nucleotide-profile derivation, threshold-free profile heterogeneity decomposition, directional Total Variation geometry, normalized-variant support-topology unit tests, sparse sample evidence tests, end-to-end CLI/schema validation, local non-committed multi-read review | `signal.sample_evidence/v8` |
| `SRS-VAR-*` | `pipeline.md` Stage 6 | `src/variant_calling/`, `src/model/variant.rs` | SNV/indel/normalization mapping tests + mixed-supporting-signal eligibility + real truth | analysis variants |
| `SRS-OUT-*` | output docs, architecture | `src/report/`, `src/pipeline/` | schema/example + publication tests | JSON schemas |
| `SRS-BAT-*` | data/batch docs | `scripts/analyze_samples.py` | Python batch tests | external orchestration behavior |
| `SRS-NFR-*` | architecture/invariants, validation | cross-cutting | CI, fuzz/property/release evidence as adopted | release evidence |
| `SRS-VAL-*` | `validation.md`, ADR-0044/0045/0048/0049/0050/0051/0052/0054, Signal validation research | `src/validation/`, `src/pipeline/validation.rs`, `src/pipeline/sample_reads.rs`, `src/sample/loci.rs`, `scripts/run_validation_corpus.py`, `scripts/analyze_validation_corpus.py`, `scripts/audit_validation_corpus.py`, `scripts/prepare_validation_curation.py`, `scripts/analyze_polyc_phase.py`, `scripts/analyze_polyc_phase_hypotheses.py`, `scripts/analyze_polyc_phase_characterization.py`, `scripts/analyze_polyc_orientation_controls.py`, `scripts/validation_corpus/` | `tests/validation.rs`, `tests/python/test_validation_corpus.py`, `tests/python/test_validation_research.py`, `tests/python/test_validation_audit.py`, `tests/python/test_validation_curation.py`, `tests/python/test_polyc_geometry.py`, `tests/python/test_polyc_phase.py`, `tests/python/test_phase_hypotheses.py`, `tests/python/test_phase_characterization.py`, `tests/python/test_polyc_orientation_controls.py`, synthetic ABIF, CI, grouped local corpus studies | ignored `signal.validation_locus/v2`, `signal.validation_corpus/v1`, descriptive `signal.validation_research/v1`, observational `signal.validation_audit/v1`, immutable `signal.validation_curation_queue/v1`, descriptive `signal.validation_polyc_phase/v1`, descriptive `signal.validation_phase_hypotheses/v1`, descriptive `signal.validation_phase_characterization/v1`, and descriptive `signal.validation_polyc_orientation_controls/v1` evidence; no production schema change |

## Navigation rule

For a behavior change:

1. locate the requirement family;
2. read the linked method/architecture document;
3. read relevant accepted ADRs;
4. read the owning `docs/src` manual and source;
5. inspect the linked tests/contracts;
6. update every affected layer in the same change.

Research documents are intentionally absent from this table because they are not current production authority.
