# Validation

Signal separates software verification from scientific validation. A green test
suite is necessary but does not by itself establish biological correctness.

## Structural gates

- exact `src/**/*.rs` ↔ `docs/src/**/*.md` mirror;
- strict TOML parse plus range and relational checks;
- Draft 2020-12 analysis-v5 and basecalls-v1 schema validation;
- Markdown links, rustdoc, rCRS source checksum/length, and `.env` policy;
- no repository backups or accidental patient/sample fixtures.

## Unit and integration verification

Unit tests cover checked binary parsing, ABIF tag/cardinality rules, FASTA
validation, peak selection and ambiguity, signal features, quality/trimming,
alignment, circular projection, normalization, variant evidence, deterministic
serialization, and atomic publication.

Integration tests construct canonical synthetic ABIF input and verify both
reference-free `signal.basecalls/v1` and reference-guided
`signal.analysis/v5`, including forward/reverse mappings, indels, circular
segments, warning summaries, strict configuration, malformed input, logs, and
no-overwrite behavior.

Focused Python tests cover batch preflight, ambiguity/collision/symlink
rejection, selected-only destructive cleanup, unselected-artifact preservation,
and partial-output behavior after a later failure.

## Differential and real-trace validation

An ignored local trace is not a golden. Before a real trace is used as release
evidence, record approval, source context, trace/reference/config checksums,
region/orientation, generating implementation revision, expected
calls/trim/alignment/variants, comparison rules, and redistribution status.

Exact fields compare exactly. Equivalent indels compare only after documented
normalization. Missing or extra variants do not pass by tolerance.

Use:

- provenanced synthetic fixtures for exact algorithmic boundaries;
- approved real AB1 traces;
- independently established expected sequences/variants where available;
- explicit acquisition/reference/configuration identity;
- documented disagreement analysis.

Data provenance and privacy rules are defined in
[operations/data.md](../operations/data.md).

## Biological validation

Rolling SNR and relative quality are not error probabilities. Validation must not
call them Phred or infer clinical sensitivity.

A behavior-changing signal cleaner must additionally preserve synthetic
secondary peaks under baseline drift, impulse noise, compressed peaks,
homopolymers, and read ends. Heteroplasmy, genotype, pathogenicity, diagnostic,
or other clinical claims require separate methods and studies.

## Performance

For release evidence, run a release build with a named 500–1,000 base approved
or synthetic trace against rCRS. Record host/toolchain, checksums, elapsed time,
and peak memory.

Current target: at most 30 seconds and 512 MiB. Resource-cap failures must occur
before large allocation.

## Release gate

All normative requirements and automated checks must pass, and at least one
approved real AB1 must have complete end-to-end evidence before describing a
scientific release as real-trace validated.

Production release evidence follows
[ADR-0018](../adr/0018-production-readiness-release-contract.md) and identifies
the exact source revision, toolchain, artifact, dependency state, automated
gates, performance evidence, and real-trace validation status.
