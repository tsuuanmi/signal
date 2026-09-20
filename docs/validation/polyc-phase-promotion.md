# Poly-C phase interpretation and weighting promotion protocol

## Scope

This protocol governs any future change that interprets internal
`signal.polyc_phase/v1` evidence as a categorical phase state, recovery state,
confidence attenuation, contribution weight, no-call, or variant/artifact decision.

The current Rust measurement is continuous evidence only. Passing software tests does not
satisfy this promotion protocol.

## Corpus and provenance

A promotion study MUST identify the exact validation corpus revision and retain:

- trace SHA-256;
- reference/configuration identities;
- source-group and specimen-group identities;
- PCR replicate, sequencing run, instrument, and amplicon metadata when available;
- selected orientation from Signal, never declared direction as scientific placement;
- holdout assignment fixed before threshold/model selection;
- truth or proxy provenance for every labelled evaluation target.

Source groups MUST NOT span development and holdout partitions.

Independent PCR replication is preferred. When unavailable, same-PCR observations MUST
not be counted as independent biological replication.

## Evidence targets

At minimum the study MUST include:

1. clean T-interrupt or otherwise phase-coherent downstream evidence;
2. C-interrupt reads with strong directional post-tract degradation;
3. structured shifted-reference windows with low residual mass;
4. high-impurity windows/read segments with persistently high residual mass;
5. incomplete-tract, profile-gap, read-end, and no-complete-window cases;
6. true downstream SNV challenge cases so a phase policy is not trained to erase real
   biological differences;
7. HV1 and HV2, forward and reverse orientations;
8. same-amplicon and cross-amplicon observations where available;
9. available sequencing-run/instrument strata;
10. recurrent loci 253, 297, 302, 16194, and 16197 as challenge context, never as
    hard-coded detector rules.

## Development and holdout

Development data MAY be used to choose:

- which continuous phase quantities enter an interpretation;
- threshold(s);
- recovery criteria;
- any mapping from evidence to reliability weight.

Holdout data MUST remain untouched until the complete rule and all parameters are frozen.

Parameter sensitivity already established for descriptive window/stride/max-offset choices
does not replace this development/holdout requirement.

## False-attenuation objective

Before fitting a reliability policy, the study MUST state an explicit maximum tolerated
false attenuation/no-call rate on clean evidence.

A policy cannot be promoted only because it improves agreement on known problematic
C-interrupt reads. Clean reads and true downstream variants are co-primary safety targets.

## Candidate/state interpretation

Any proposed categorical state MUST be defined from explicit continuous quantities and
must preserve evidence availability:

```text
not applicable
insufficient evidence
measured evidence
```

`NotApplicable` and `Insufficient` MUST NOT be folded into a clean/stable state.

If a winning candidate offset is proposed, the study MUST justify:

- minimum informative positions;
- separation from neighboring candidates;
- behavior when several offsets predict the same local shifted base;
- behavior when shifted-reference mass is high but residual mass is also high;
- behavior across adjacent windows.

## Recovery

A recovery rule MUST be evidence-based and read-local. Fixed genomic distance alone is not
acceptable.

The study MUST evaluate whether recovery remains stable across:

- window starts;
- tract/orientation strata;
- reads ending near the apparent recovery point;
- profile gaps.

## Weighting or no-call policy

Any phase-derived weighting must explicitly amend ADR-0040 / SRS-SAMPLE-019 rather than
adding a parallel hidden weight.

The evaluation MUST report at least:

- clean-evidence false attenuation;
- affected-evidence sensitivity;
- true-SNV retention;
- proportion of reads/loci with insufficient phase evidence;
- changes in sample-level support topology and effective contribution;
- behavior by tract/orientation/amplicon;
- failure cases reviewed manually.

A no-call policy requires the same evidence plus explicit accounting of newly missing
results.

## Reproducibility

Before promotion, rerun the frozen method on the same corpus and verify deterministic
identical phase measurement identities/quantities within the repository's numerical
contract.

Where multiple runs/instruments or PCR replicates exist, report reproducibility separately
instead of pooling them into one nominal N.

## Promotion record

A production interpretation/weighting PR MUST include:

- the frozen rule;
- selected parameter values;
- development results;
- untouched holdout results;
- challenge-set results;
- known limitations;
- the ADR/SRS changes that authorize the behavior;
- exact automated regression fixtures derived from non-identifying synthetic or approved
  data.

Without that record, `signal.polyc_phase/v1` remains observation-only internal evidence.
