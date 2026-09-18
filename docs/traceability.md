# Documentation and Implementation Traceability

This map helps developers and agents move from intent to implementation without duplicating the specification.

| Requirement family | Current method / architecture | Owning implementation | Primary tests / evidence | Public contract |
|---|---|---|---|---|
| `SRS-IN-*` | `pipeline.md`, `architecture.md` | `src/trace/`, `src/reference/`, `src/cli/` | parser/reference/CLI tests, synthetic ABIF | CLI/config contracts |
| `SRS-CFG-*` | `configuration.md` | `src/config/` | strict TOML/config tests | `config/signal.toml` semantics |
| `SRS-BC-*` | `pipeline.md` Stage 2 | `src/basecalling/`, `src/model/basecalls.rs` | basecalling unit tests + approved trace comparison | `signal.basecalls/v1`, mapped calls in analysis |
| `SRS-SIG-*` | `signal-processing.md` | `src/signal_processing/` | signal feature boundary tests | noisy-region projections |
| `SRS-QC-*` | `pipeline.md` Stage 4 | `src/quality_control/` | quality/trim unit + real-read review | trim + supporting relative quality |
| `SRS-ALN-*` | `pipeline.md` Stage 5 + read-observation boundary | `src/alignment/`, `src/model/alignment.rs`, `src/model/read_observation.rs` | orientation/traceback/circular tests | analysis alignment summary |
| `SRS-SAMPLE-*` | ADR-0023, architecture invariants | `src/sample/`, `src/model/sample_evidence.rs`, `src/pipeline/sample.rs` | sparse sample evidence unit tests, CLI/schema validation, real AB0444 multi-read review | `signal.sample_evidence/v2` |
| `SRS-VAR-*` | `pipeline.md` Stage 6 | `src/variant_calling/`, `src/model/variant.rs` | SNV/indel/normalization mapping tests + real truth | analysis variants |
| `SRS-OUT-*` | output docs, architecture | `src/report/`, `src/pipeline/` | schema/example + publication tests | JSON schemas |
| `SRS-BAT-*` | data/batch docs | `scripts/analyze_samples.py` | Python batch tests | external orchestration behavior |
| `SRS-NFR-*`, `SRS-VAL-*` | architecture/invariants, validation | cross-cutting | CI, fuzz/property/release evidence as adopted | release evidence |

## Navigation rule

For a behavior change:

1. locate the requirement family;
2. read the linked method/architecture document;
3. read relevant accepted ADRs;
4. read the owning `docs/src` manual and source;
5. inspect the linked tests/contracts;
6. update every affected layer in the same change.

Research documents are intentionally absent from this table because they are not current production authority.
