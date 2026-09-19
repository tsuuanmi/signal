# ADR-0050: Keep validation audit strata observational and separate from truth

- **Status:** Accepted
- **Date:** 2026-09-19

## Context

The first full local validation corpus contains 89 cases, 360 reads, tens of thousands of
covered loci, and several distinct forms of real-world challenge evidence. Low alignment
identity, high noisy-call burden, aggressive trimming, short callable coverage, and
mixed reference/alternate evidence near retained read edges do not have the same
biological meaning and must not be collapsed into a generic "bad sample" label.

The corpus still has unreviewed biological truth and an unassigned development/holdout
split. Promoting empirical outlier rules directly into threshold fitting or production QC
would therefore leak descriptive corpus structure into scientific interpretation.

## Decision

Signal adds a separate external validation-audit layer,
`scripts/audit_validation_corpus.py`, producing
`signal.validation_audit/v1` under ignored `validation-results/`.

The audit consumes:

- one completed `signal.validation_corpus/v1`;
- its case validation logs;
- one hash-matched `signal.validation_research/v1` dataset.

The audit never edits the manifest, truth fields, threshold-fit inclusion, holdout group,
production configuration, or production result schemas.

### Read strata

Read outlier boundaries are empirical nearest-rank tails within
`amplicon_id × declared_direction` strata:

- `alignment_challenge`: callable identity at or below stratum p05;
- `high_noise`: noisy-call fraction at or above stratum p95;
- `aggressive_trim`: retained fraction at or below stratum p05;
- `short_coverage`: callable columns at or below stratum p05.

A stratum requires at least 20 reads before any of these four relative flags can be
assigned. Smaller strata are marked `unbenchmarked_stratum` instead of borrowing a
threshold from an unrelated primer/direction group.

Inferred orientation differing from declared validation metadata is recorded separately as
`orientation_disagreement`.

Operational logs are parsed only for deterministic read-stage metrics and are bound back
to corpus reads by SHA-256. Run IDs, timestamps, local paths, and log text are not copied
into audit outputs.

### Locus strata

Every locus with both reference and alternate read observations is retained in
`locus-audit.csv`.

`edge_discordance` is an observational context flag when:

1. the locus has both reference and alternate read observations;
2. at least one alternate observation lies within 10 calls of that read's retained trim
   boundary; and
3. alternate evidence is not observed from both selected orientations.

The rule does not classify the alternate observation as artifact or biological mixture.

### Case strata

Case audit rows summarize read flags and locus context. A case receives
`short_coverage_cluster` when at least two reads are short-coverage outliers.

`geometry_challenge` is corpus-relative: the case p95
`total_profile_heterogeneity` is at or above the empirical p95 across case-level p95
values.

Case flags form a review shortlist only. They do not exclude a case or read from later
truth curation or validation studies.

## Consequences

- Distinct technical challenge modes remain inspectable instead of being collapsed into a
  single quality verdict.
- Small primer/direction strata cannot silently inherit unrelated empirical boundaries.
- Mixed loci can be reviewed together with read-edge/noisy/orientation context before
  any threshold is selected.
- Audit outputs are deterministic, no-overwrite, hash-bound to the corpus and research
  dataset, and contain no local AB1 path.
- Threshold fitting still requires independent truth, a frozen development/holdout split,
  and the promotion gates in `threshold-research.md`.

## Non-goals

This ADR introduces no biological truth label, artifact verdict, heteroplasmy verdict,
read rejection, sample rejection, production QC gate, candidate geometry cutoff, LoB/LoD
claim, classifier, or compatibility output.
