# Validation Measurement Export

## Purpose

Define the data boundary used for empirical threshold research without changing the public `signal.sample_evidence/v7` contract.

## Why a separate export exists

Production sample JSON intentionally keeps sparse differential-locus evidence and omits internal nucleotide-profile geometry. Aggregate operational logs consume geometry but cannot support per-locus null distributions or threshold fitting.

Clean reference-matching loci are essential negative controls. Exporting only `locus_differences` would bias threshold research by excluding those loci.

## Implemented boundary

`signal-validation` is a separate validation binary. It:

- reuses authoritative trace decoding, basecalling, signal processing, QC, alignment, variant calling, sample validation, and profile-geometry code;
- uses the same generic sample-locus builder as production;
- selects every covered reference locus rather than only differential loci;
- emits deterministic JSONL ordered by reference position;
- publishes atomically without overwrite;
- writes only under ignored `validation-results/`;
- never applies truth labels, candidate thresholds, or biological interpretation;
- never changes the production sample result schema.

Example:

```bash
SIGNAL_CONFIG=config/signal.toml \
  cargo run --release --bin signal-validation -- \
  validation-001 trace-a.ab1 trace-b.ab1 \
  --reference references/rCRS.fasta
```

Output:

```text
validation-results/validation-001.jsonl
```

Operational trace-stage records are written to `logs/validation-001.validation.log` unless `SIGNAL_LOG_DIR` is overridden.

## Row schema

Each line is one `signal.validation_locus/v2` object. v2 replaces the research-only v1 schema and retains the same locus-level aggregates plus one nested `observations[]` diagnostic record per read.

~~~text
schema_version
signal_version
sample_id
reference_sha256
configuration_sha256
position_1based
reference_base

reads
forward_reads
reverse_reads
reference_reads
alternate_reads
unresolved_reads
deletion_reads
profile_reads
profile_forward_reads
profile_reverse_reads

contributors
forward_contributors
reverse_contributors

mean_a
mean_c
mean_g
mean_t

within_profile_impurity
between_profile_dispersion
total_profile_heterogeneity

forward_within_profile_impurity
forward_between_profile_dispersion
forward_total_profile_heterogeneity

reverse_within_profile_impurity
reverse_between_profile_dispersion
reverse_total_profile_heterogeneity

directional_profile_distance

noisy_observations
missing_profile_observations
deletion_observations
~~~

Optional profile/geometry values are JSON `null` when the required evidence partition does not exist.

Truth labels, prepared mixture fractions, PCR replicate IDs, run IDs, artifact tags, and holdout grouping remain external validation-manifest metadata. They are joined after export; Signal does not infer them.

## Determinism and publication

For identical traces, reference, configuration, and Signal version, row content and ordering are deterministic. Operational timestamps remain confined to logs.

The exporter follows the same no-overwrite publication rule as production results. A repeated export must use a clean validation output target rather than silently replacing prior measurements.

## Privacy

Per-locus measurements can reveal biological differences and therefore inherit the source AB1 privacy policy. Real JSONL, local truth manifests, and joined analysis tables must remain ignored/local unless explicit redistribution approval exists.

## Validation status

Synthetic integration tests verify that:

- all-reference covered loci appear in validation output;
- production `results/` is not created by the validation binary;
- profile geometry is exported on clean covered loci;
- the exporter refuses to overwrite an existing measurement file.

This exporter is measurement infrastructure only. Threshold selection remains governed by `validation-corpus.md` and `threshold-research.md`.
