# Tracy Ideas Ranked by ROI

This is the compact prioritization layer. Detailed rationale lives in the focused research documents linked from [`README.md`](README.md) and the implementation-level findings in [`source-audit.md`](source-audit.md).

This ranking is relative to Signal's current scope: deterministic Sanger AB1 processing for short references, with basecalling, alignment, and conservative variant reporting already implemented.

**Promotion note (2026-09-19):** rank 1 is production behavior via ADR-0027 / `signal.primary_difference/v4`; rank 2's PLOC/vendor cardinality, PLOC-spacing, exact clipping, and event-signal-scale foundation is promoted via ADR-0031 while richer artifact classification remains research; rank 3 is formalized via ADR-0028 as basecall-independent `LocusEvidence -> EvidenceProfile`; rank 4 is promoted via ADR-0029 as fixed-point profile-aware Gotoh placement; the rank-5 reconciliation foundation is promoted through ADR-0023 through ADR-0025 plus ADR-0030's explicit overlap/admission graph; and rank 6 now has its local coverage foundation via ADR-0032, factorized normalized-variant read/eligibility/orientation support via ADR-0033, and internal reference-oriented basecall-independent profile retention via ADR-0034, differential-locus orientation/state topology via ADR-0035, and observation-only local noisy-region context via ADR-0036, and structural nucleotide-contribution eligibility via ADR-0037 while quality/noise weighting and decision policy remain deferred. The research rationale remains here; root SRS/ADR/source are authoritative for current behavior.

ROI combines expected biological correctness/review value, reuse of existing Signal evidence, implementation and validation cost, architectural disruption, and risk of unsupported biological claims.

## Ranking

| Rank | Tracy lesson / opportunity | ROI | Signal interpretation |
|---|---|---|---|
| 1 | Use secondary/mixed signal in simple-variant eligibility | Very high | Prevent a strongest-base difference from being presented as an ordinary clean SNV when the same locus has meaningful competing signal. |
| 2 | PLOC completeness + artifact-resilience validation | Very high | Foundation promoted via ADR-0031: preserve vendor/PLOC cardinality mismatch, PLOC spacing, exact clipping, and event-signal imbalance as evidence; broad-peak/baseline/neighbor artifact classification remains research. |
| 3 | Evidence profile independent of thresholded basecall membership | Very high | Promoted via ADR-0028: preserve measured A/C/G/T evidence rather than rebuilding a profile only from channels already admitted by the caller. |
| 4 | Trace-profile-aware alignment | Very high | Promoted via ADR-0029: reuse the existing Gotoh engine with fixed-point evidence-aware substitution scoring and explicit numeric/tie semantics. |
| 5 | Forward/reverse trace reconciliation | High | Promoted as generic N-read reference-coordinate evidence plus ADR-0030 overlap admission; F/R remains a validation case rather than a pair-only domain. |
| 6 | Reference-guided multi-trace consensus | High, post-MVP | Coverage/orientation topology promoted via ADR-0032 and differential-locus state/orientation topology via ADR-0035; consensus contributor and allele/gap decision policy still must avoid quality-blind majority vote. |
| 7 | Explicit review/evidence artifact | Medium-high | Preserve trace/call/reference provenance for manual review without bloating compact production JSON. |
| 8 | Persistent mixed-signal/post-indel shift detection | Medium-high research | Detect a transition in signal phase/cleanliness without immediately assigning genotype or heteroplasmy. |
| 9 | Wild-type AB1 profile comparison | Medium | Useful for assay/control workflows, but less central than FASTA/rCRS comparison for mtDNA. |
| 10 | VCF/BCF projection | Medium | Useful interoperability after the typed JSON contract is stable; provenance fields are valuable, genotype semantics are not directly portable. |
| 11 | Two-allele decomposition | Low now | Useful mechanism research, but Tracy's reference-threading and diploid assumptions are not appropriate as a direct mtDNA model. |
| 12 | Genome FM-index/search | Very low now | Signal's <=50 kb short-reference scope does not justify the extra machinery. |
| 13 | De novo chromatogram assembly | Very low now | Reference-guided reconciliation is simpler and more auditable for the intended mtDNA workflow. |
| 14 | SCF/FASTQ convenience output | Very low | Does not materially improve biological correctness; FASTQ also implies quality semantics that Signal has not calibrated. |

## Why artifact/PLOC validation moved near the top

Tracy's public issue history exposes two operational failure modes that are more fundamental than profile alignment:

- Tracy requires the original instrument peak-location series and cannot continue when that series terminates early.
- Tracy currently cannot handle some high-amplitude dye-blob-like artifacts that dwarf usable sequence signal.

Signal already has stronger typed parsing and robust local SNR observations, but the current basecaller still depends on PLOC and the SNR layer is observation-only. Therefore the next profile architecture should not be considered sufficient until the input/event evidence is deliberately stress-tested.

## Why not copy Tracy's profile formula

Tracy's profile is built after primary/secondary calling. Channels represented by those calls are normalized, and missing called-signal mass softens the vector toward uniform A/C/G/T.

That is elegant and practical, but it means the "continuous" profile is still gated by a discrete threshold decision. Signal should instead define the profile directly from its channel evidence and let primary/ambiguity calls be downstream projections.

## Why consensus needs a separate design

Tracy pairwise consensus is profile-aware, but multi-trace assembly ultimately uses character majority voting without per-base quality. Public issue discussion confirms that base-vs-gap conflicts are especially difficult because a gap lacks an equivalent chromatogram quality.

Signal should therefore treat nucleotide support and indel/gap-event support as related but distinct evidence types rather than force both into an unweighted vote.

## Ideas intentionally deferred

### Genotype and allele-fraction semantics

A secondary peak in mtDNA can reflect heteroplasmy, noise, pull-up, co-amplification, NUMTs, poor peak separation, or a mixed-length template. Signal should not map Tracy's diploid genotype or signal-reconstruction coefficients directly onto mtDNA heteroplasmy.

### Genome indexing

Tracy needs indexed search because it supports gigabase-scale references. Signal currently uses one short reference record and bounded alignment. Until that scope changes, FM indexing has poor ROI.

### De novo assembly

For the intended mtDNA workflow, reference-guided overlap reconciliation has clearer coordinates, fewer failure modes, and better auditability.
