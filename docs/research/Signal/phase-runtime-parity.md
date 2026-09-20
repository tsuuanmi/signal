# Phase runtime parity evidence — 2026-09-20

## Status

Completed local validation evidence for `signal.polyc_phase/v1` measurement parity.

This record establishes parity between the production Rust read-local phase measurement and
the completed Python research phase-hypothesis implementation for the checked corpus. It
does **not** define or validate a phase state, threshold, recovery rule, confidence weight,
attenuation rule, no-call policy, variant rule, or sample-contribution policy.

## Question

Does the production Rust `ReadObservation.phase` measurement reproduce the established
Python research window/candidate evidence without changing geometry or interpretation?

The comparison boundary is:

```text
signal.validation_phase_hypotheses/v1  ─┐
                                         ├─ exact structural + tolerant numeric parity
signal.validation_phase_runtime/v1    ──┘
```

The parity checker consumes completed artifacts only. It does not regenerate windows,
candidate contributions, or phase geometry.

## Evidence bundle

Reviewed bundle:

```text
phase-runtime-parity.zip
SHA-256 caa22931ee555ddacc0c960a749c1f626403c3da351f4012b7a6895b371298dd
```

The bundle contains:

- 89 `*.phase-runtime/` artifacts produced by the Rust validation path;
- one completed `signal.validation_phase_hypotheses/v1` evidence set under
  `rust-v1/`;
- the same completed research evidence set duplicated under `circular-v1/`;
- parity output for both research-directory names.

`rust-v1` and `circular-v1` are byte-identical for `index.json`, `windows.csv`,
and `hypotheses.csv`. They therefore count as one research evidence set, not two
independent validation replications.

Research payload identities:

```text
index.json       e79299e023f55f851fd9a7735058fb4d2e9dbf88bdbc61ba81191066204f024e
windows.csv      92c5bc6794bdb2afba5049b34959ec4b770b3560afbbcadc7f513eb539ee1378
hypotheses.csv   7c2546fc85e3ffd69464d19e28b4d9dc67c7a50aae46b54a25e0dab1ce72d4a3
```

## Provenance

All 89 runtime artifacts agree on:

```text
signal version         0.1.0
source method          signal.polyc_phase/v1
reference SHA-256      f156ff3f65bbcc80c7ebb9936dceb96b1477b4f8f535c4e1dbe7baea225cbc66
configuration SHA-256  ae03a65a199dca02173bae66973b357f08bb18e5983146ba21a1e788861664fd
```

The research artifact records the same Signal version, reference identity, configuration
identity, and production-v1 method constants:

```text
window size            25 profile-bearing observations
window step            5 profile-bearing observations
candidate offsets      -5,-4,-3,-2,-1,+1,+2,+3,+4,+5
candidate selection    none; complete curve retained
```

The supplied evidence bundle does not retain the exact generating Git commit SHA. Repository
`main` at review time contained the merged parity checker from PR #49, but that fact is
not sufficient to assign an exact runtime revision to the bundle. Future formal validation
bundles should retain `git rev-parse HEAD` alongside the parity result.

## Corpus coverage

The runtime evidence contains:

| Measure | Count |
|---|---:|
| validation cases | 89 |
| unique reads | 360 |
| applicable reads | 360 |
| tract records | 720 |
| measured tracts | 255 |
| insufficient tracts | 465 |
| complete windows | 11,231 |
| candidate records | 112,310 |
| cases with zero complete windows | 13 |

Explicit insufficiency remained visible rather than being coerced into measured evidence:

| Insufficiency | Count |
|---|---:|
| `no_tract_coverage` | 362 |
| `incomplete_tract_coverage` | 29 |
| `no_complete_profile_window` | 74 |

No `no_call_backed_tract_span` record occurred in this checked corpus.

## Structural parity

The direct checker joined windows by:

```text
read_sha256
tract_id
start_distance_after_tract
end_distance_after_tract
```

It then compared start/end original call indexes and profile-observation counts exactly.
Candidate identity adds `reference_offset_in_read_order`, and informative-position counts
compare exactly.

Observed result:

```text
research windows       = 11231
runtime windows        = 11231
missing windows        = 0
extra windows          = 0
call index diff        = 0
profile count diff     = 0

research candidates    = 112310
runtime candidates     = 112310
missing candidates     = 0
extra candidates       = 0
candidate count diff   = 0
informative count diff = 0
numeric presence diff  = 0
```

This establishes exact parity for the checked structural identities and counts.

## Numerical parity

The checker compared window impurity and candidate zero/shifted/residual masses with an
absolute tolerance of `1e-12`.

Observed result:

```text
max numeric delta      = 5.5511151231257827e-16
numeric tolerance      = 9.9999999999999998e-13
parity                 = PASS
```

The maximum observed difference is approximately three orders of magnitude below the
declared tolerance and is consistent with ordinary floating-point evaluation-order
differences. No structural mismatch accompanied the numerical delta.

## Artifact integrity review

The supplied runtime bundle was additionally checked for internal consistency:

- all 89 runtime `index.json` files referenced existing CSV payloads;
- declared per-file SHA-256 values matched the supplied CSV bytes;
- declared window/candidate row counts matched the actual tables;
- all 360 read SHA-256 identities were unique across the checked runtime artifacts;
- every complete window retained exactly 25 profile observations;
- every complete window retained the full ten-candidate offset set;
- window and candidate identity keys were unique;
- candidates with zero informative positions retained absent numeric masses;
- informative candidates retained zero/shifted/residual masses with consistent presence.

These checks validate the evidence bundle shape; they do not substitute for biological
validation of a future interpretation policy.

## Conclusion

For this 89-case / 360-read corpus, the production Rust implementation and the established
Python research implementation are structurally identical for every checked window and
candidate and numerically equivalent within `5.5511151231257827e-16`.

The evidence therefore supports the following narrow conclusion:

```text
research Python phase measurement
              ↓
      validated measurement parity
              ↓
production Rust ReadPhaseEvidence
```

The measurement implementation is no longer the open scientific question addressed by the
next phase of work.

The next question is interpretation: whether the continuous evidence can support useful
window/tract evidence patterns and recovery transitions without suppressing clean evidence or
true downstream sequence differences. The research design is frozen in
[polyc-phase-interpretation-study.md](polyc-phase-interpretation-study.md), while production
promotion remains governed by `docs/validation/polyc-phase-promotion.md`. Python remains a
research/validation harness; any promoted interpretation must be implemented authoritatively
in the Rust core before it can affect production behavior.

## Reproducibility follow-up

A future parity evidence bundle should additionally retain:

- exact generating Git commit SHA;
- parity command and tolerance;
- research artifact directory identity without duplicate aliases;
- runtime artifact root identity;
- bundle SHA-256.

Those additions improve provenance only; they are not required to reinterpret the clean
parity result recorded here.
