# Validation Measurement Export

## Purpose

Define the data boundary required for empirical threshold research without changing the
public `signal.sample_evidence/v7` contract.

## Problem

Current production JSON intentionally omits internal per-locus nucleotide-profile geometry.
Aggregate operational logs consume geometry, but aggregate sums are insufficient for
threshold fitting.

Threshold research therefore needs a dedicated local measurement export before any
empirical threshold can be estimated.

## Design constraints

The exporter must:

- be explicitly validation/research tooling, not a public scientific result contract;
- reuse authoritative internal `SampleEvidence` rather than recomputing signal features;
- emit one row per retained differential locus;
- preserve contributor topology and threshold-free geometry;
- keep real outputs under ignored local paths;
- never mutate the production sample schema;
- never invent missing profiles or gap evidence;
- never apply a candidate threshold while exporting measurements.

## Proposed row

~~~text
run_id
sample_research_id
reference_sha256
configuration_sha256
position_1based

reads
forward_reads
reverse_reads
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

Truth labels and prepared mixture fractions should be joined from the local validation
manifest after export. The measurement tool should not infer biological truth.

## Privacy

Per-locus measurements can reveal biological differences and therefore inherit the source
AB1 privacy policy.

Default destination should be an ignored local tree such as:

~~~text
validation-results/
~~~

No real measurement table belongs in Git.

## Next implementation gate

Before implementing the exporter:

1. freeze the row schema above;
2. decide CSV versus JSONL based on analysis workflow;
3. define deterministic ordering;
4. add synthetic fixture tests;
5. ensure the tool cannot silently publish into production `results/`;
6. document exact command and provenance fields.

The exporter is the next code-enabling step for threshold research. It should be a single
authoritative path, not an environment-variable debug mode or hidden compatibility output.
