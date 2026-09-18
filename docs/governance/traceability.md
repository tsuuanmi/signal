# Documentation and Implementation Traceability

This map helps developers and agents move from intent to implementation without
duplicating the specification.

| Requirement family | Current method / architecture | Owning implementation | Primary tests / evidence | Public contract |
|---|---|---|---|---|
| `SRS-IN-*` | `docs/methods/pipeline.md`, `docs/architecture/overview.md` | `src/trace/`, `src/reference/`, `src/cli/` | parser/reference/CLI tests, synthetic ABIF | CLI/config contracts |
| `SRS-CFG-*` | `docs/contracts/README.md` | `src/config/` | strict TOML/config tests | `config/signal.toml` + typed validation |
| `SRS-BC-*` | `docs/methods/pipeline.md` Stage 2 | `src/basecalling/`, `src/model/basecalls.rs` | basecalling unit tests + approved trace comparison | `signal.basecalls/v1` |
| `SRS-SIG-*` | `docs/methods/signal-processing.md` | `src/signal_processing/` | signal feature boundary tests | noisy-region projections |
| `SRS-QC-*` | `docs/methods/pipeline.md` Stage 4 | `src/quality_control/` | quality/trim unit + real-read review | trim + supporting relative quality |
| `SRS-ALN-*` | `docs/methods/pipeline.md` Stage 5 | `src/alignment/`, `src/model/alignment.rs` | orientation/traceback/circular tests | analysis alignment summary |
| `SRS-VAR-*` | `docs/methods/pipeline.md` Stage 6 | `src/variant_calling/`, `src/model/variant.rs` | SNV/indel/normalization mapping tests + real truth | analysis variants |
| `SRS-OUT-*` | `docs/contracts/README.md`, architecture | `src/report/`, `src/pipeline/` | schema/example + publication tests | JSON schemas |
| `SRS-BAT-*` | operations/data policy | `scripts/analyze_samples.py` | Python batch tests | external orchestration behavior |
| `SRS-NFR-*`, `SRS-VAL-*` | architecture/invariants, validation | cross-cutting | CI, fuzz/property/release evidence as adopted | release evidence |

## Navigation rule

For a behavior change:

1. locate the requirement family;
2. read the linked method/architecture document;
3. read relevant accepted ADRs;
4. read the owning `docs/src` manual and source;
5. inspect the linked tests/contracts;
6. update every affected layer in the same change.

Research documents are intentionally absent because they are not current
production authority.
