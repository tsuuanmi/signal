# Independent Read Processing and Sample Reconciliation

This document focuses on a central Tracy lesson for Signal's future sample-level
architecture: multiple Sanger traces should be processed independently first and
only reconciled after each read has become an explicit reference-coordinate
observation.

The motivating mtDNA shape is not merely one forward/reverse pair:

~~~text
HV1F
HV1R
HV2F
HV3R
...
~~~

where reads from different amplicons can overlap each other. For example,
HV2F and HV3R may cover the same reference interval even though they are not
the canonical F/R pair of one amplicon.

## Tracy has two distinct multi-trace models

### Pairwise tracy consensus

The pairwise command requires exactly two trace files.

For each trace Tracy independently:

1. decodes the chromatogram;
2. re-basecalls it;
3. trims it;
4. constructs a trace profile.

Then it:

1. keeps the first trace orientation fixed;
2. scores the second trace in forward and reverse-complement orientation;
3. chooses the better orientation;
4. performs profile-to-profile overlap alignment;
5. requires minimum aligned overlap (default 25);
6. requires minimum primary-character match fraction (default 0.5);
7. combines overlapping profile columns;
8. optionally emits non-overlapping flanks as a union.

This is suitable for:

~~~text
one locus
+ two traces
+ likely F/R pair
~~~

It is not the correct abstraction for a tiled sample containing many reads.

### Multi-trace tracy assemble

Reference-guided assemble is closer to the architecture Signal needs.

For every trace independently, Tracy performs:

~~~text
decode
  ->
basecall
  ->
trim
  ->
trace profile
  ->
score forward/reverse against reference
  ->
admit or reject
~~~

Only then are admitted traces combined.

The reference-guided assembly then:

1. sorts admitted traces by alignment score;
2. aligns the best trace to the reference profile;
3. repeatedly converts the growing alignment into a profile;
4. aligns the next read profile to that growing alignment profile;
5. produces a multiple alignment;
6. calls a final consensus across alignment columns.

Therefore Tracy already demonstrates the correct high-level separation:

~~~text
per-trace scientific processing
       !=
multi-trace reconciliation
~~~

Signal should preserve this separation more strictly than Tracy does.

## Signal should not merge F/R pairs first

A tempting design is:

~~~text
HV1F + HV1R -> HV1 consensus
HV2F + HV2R -> HV2 consensus
HV3F + HV3R -> HV3 consensus

then merge amplicon consensuses
~~~

This is simple, but it destroys useful evidence topology.

Consider:

~~~text
HV1F ------>
      <------ HV1R

             HV2F ------------>
                    <------------ HV3R
~~~

If HV2F and HV3R overlap, they are valid cross-amplicon observations of the
same sample coordinates. Pair-first merging makes their relationship secondary
and can hide which original read supported a locus.

Recommended:

~~~text
HV1F -> ReadObservation --+
HV1R -> ReadObservation --+
HV2F -> ReadObservation --+--> SampleEvidence
HV3R -> ReadObservation --+
                           |
                           v
                     reconciliation
~~~

The F/R relationship remains metadata and evidence topology; it is not an
intermediate data-collapse boundary.

## ReadObservation is the aggregation boundary

Every AB1 should complete the same single-read pipeline before entering the
sample layer:

~~~text
AB1
 -> decode
 -> basecall / locus evidence
 -> signal observations
 -> QC / trim
 -> alignment
 -> reference-coordinate projection
 -> ReadObservation
~~~

A ReadObservation should be immutable and retain provenance to the original
trace/call/PLOC evidence.

The sample layer should not re-basecall raw chromatograms, silently re-trim
reads, rewrite per-read orientation, modify per-read evidence, or use another
read to rescue an invalid basecall.

Reconciliation creates new sample-level interpretation while preserving every
read-level observation.

## Coordinate/event space, not pair space

Aggregation should be keyed by biological coordinate/event identity.

For substitutions:

~~~text
reference position 73
  <- HV1F observation
  <- HV1R observation
  <- HV2F observation
  <- HV3R observation
~~~

For insertions, the aggregation key needs an anchored insertion event rather
than just a nucleotide position.

For deletions, the aggregation key needs the normalized deleted reference span
and placement context.

Conceptually:

~~~rust
enum SampleObservationKey {
    ReferenceBase(ReferencePosition),
    Insertion(InsertionAnchor),
    Deletion(DeletionSpan),
}
~~~

This makes cross-amplicon overlap natural.

## Amplicon and direction are evidence dimensions

The sample layer always knows read identity, derived orientation, and mapped
reference span from the authoritative alignment.

Amplicon identity, primer identity, nominal direction, technical replicate
group, and assay/run grouping are optional declared metadata when available.

These fields enrich support topology and provenance; they do not decide which
reads are allowed to meet.

Thus HV1F and HV1R may be described as same-amplicon opposite-direction support
when those labels are supplied, while HV2F and HV3R may be described as
different-amplicon overlap. Both can contribute at a shared coordinate even when
no assay labels are supplied.

## Do not compress support topology into one ordinal enum

A hierarchy such as:

~~~text
SingleRead
SameDirectionReplicate
Bidirectional
IndependentAmplicon
~~~

is convenient but lossy.

These are qualitatively different:

~~~text
2 reads / 2 directions / 1 amplicon
2 reads / 1 direction  / 2 amplicons
2 reads / 2 directions / 2 amplicons
~~~

Prefer factorized support:

~~~rust
struct SupportTopology {
    read_count: usize,

    // Derived from alignment.
    forward_read_count: usize,
    reverse_read_count: usize,

    // Optional declared assay grouping.
    declared_amplicon_count: Option<usize>,
    technical_replicate_group_count: Option<usize>,
}
~~~

Avoid the word independent unless assay design actually justifies biological
independence. Different primers or amplicons reduce some shared artifacts but
do not automatically imply independent molecules.

## SampleEvidence before SampleConsensus

The primary sample object should be an evidence aggregation, not a flattened
consensus string.

Recommended order:

~~~text
ReadObservation[]
      |
      v
SampleEvidence
      |
      +--> per-coordinate nucleotide evidence
      +--> insertion/deletion event evidence
      +--> conflicts
      +--> coverage/support topology
      |
      v
SampleInterpretation
      |
      +--> consensus states
      +--> sample variants
      +--> QC/discordance
      |
      v
optional consensus sequence projection
~~~

This is stronger than:

~~~text
reads -> consensus string -> diff against reference
~~~

because a consensus string cannot faithfully represent high-confidence
disagreement, reproducible mixed evidence, competing indel placements, support
topology, uncovered regions, or read-specific provenance.

## Sample variants should not be called from a flattened consensus string

A sample variant should be derived from aggregated event evidence.

For an SNV:

~~~text
reference A

HV1F: strong G
HV1R: strong G
HV2F: strong G
HV3R: strong G

=> sample SNV candidate A>G
   with explicit contributing read/direction/amplicon topology
~~~

For conflict:

~~~text
HV1F: strong G
HV1R: strong G
HV2F: strong A
HV3R: strong A
~~~

The correct state may be Discordant or a mixed-signal research candidate. A
majority consensus string is not enough to preserve the problem.

## Reference-guided reconciliation is simpler than progressive MSA for mtDNA

Tracy reference-guided assembly progressively aligns reads to a growing MSA
profile. That is useful when the system needs a conventional multiple alignment.

Signal already has a canonical mtDNA reference coordinate system. Therefore the
simpler first design is:

~~~text
independent read alignments
      ->
reference-coordinate observations
      ->
coordinate/event aggregation
~~~

rather than rebuilding a whole progressive MSA as the core sample model.

A review UI can later render a gapped multi-read alignment from stored
coordinate/event mappings without making that rendering the scientific source
of truth.

## Read admission remains per-read

Before a read contributes, evaluate it independently:

- valid read pipeline result;
- sufficient retained evidence;
- unique/acceptable evidence-derived reference placement;
- artifact burden;
- alignment quality;
- enough mapped evidence to contribute locally.

Optional declared amplicon/direction/primer metadata is checked only after
mapping and should normally produce provenance/QC warnings rather than change
placement or admission.

A weak read should not be admitted merely because other reads support the same
sequence. That would allow sample expectation to leak backward into read
evidence.

## Local contribution can be more granular than global admission

A read may be globally admissible but locally weak.

Therefore distinguish:

~~~text
read admission
~~~

from:

~~~text
per-locus contribution eligibility
~~~

For example a read can contribute positions 100..500 but be suppressed at a
noisy tail around 490..500.

## Missing canonical pair is not a sample failure

If a manifest contains:

~~~text
HV1F
HV1R
HV2F
HV3R
~~~

Signal should not require HV2R or HV3F merely to form a sample result.

Every admitted read contributes where it maps. Support topology records which
directions and amplicons exist. Coverage gaps and single-direction regions
remain explicit.

## Recommended domain model

~~~rust
struct SampleEvidence {
    sample_id: SampleId,
    reads: Vec<ReadObservation>,
    loci: Vec<LocusAggregate>,
    events: Vec<EventAggregate>,
    coverage: CoverageMap,
}

struct LocusAggregate {
    position: ReferencePosition,
    observations: Vec<ReadBaseObservation>,
    support: SupportTopology,
    state: AggregateState,
}

struct EventAggregate {
    key: SampleObservationKey,
    observations: Vec<ReadEventObservation>,
    support: SupportTopology,
}
~~~

The exact Rust shape should be decided later; the key contract is the stage
boundary.

## Tracy lesson

The most important thing to copy from Tracy is not its final consensus caller.

It is the workflow:

~~~text
process every trace first
then reason across traces
~~~

Signal should improve the second half by preserving typed evidence instead of
collapsing the growing sample into character-majority consensus.


## Coverage and orientation are derived observations

Names such as HV1F, HV1R, HV2F, or HV3R must not be scientific placement
instructions.

For the default mtDNA workflow:

~~~text
AB1
 -> independent read pipeline
 -> alignment against complete circular reference
 -> derived orientation
 -> derived mapped reference segments
~~~

Only after those values exist may optional assay metadata be compared against
them.

Therefore:

~~~text
filename / amplicon label / nominal direction
    !=
alignment prior
~~~

A read mislabeled as HV2F but mapping strongly to another region should remain
mapped to the evidence-supported region and receive a metadata/QC discrepancy.

This also means an unlabeled set of AB1 files can still be reconciled: the
system discovers overlap from their mapped coordinates.

A useful reproducibility invariant is:

~~~text
same AB1
+ same reference
+ same config
+ same Signal version
=
same orientation and mapped segments
~~~

regardless of filename or optional amplicon/direction labels.


## Support topology must distinguish derived and declared dimensions

Not every support dimension has the same epistemic status.

Derived from scientific alignment:

~~~text
read count
mapped span
forward/reverse orientation counts
coverage at each coordinate/event
~~~

Optional declared metadata:

~~~text
amplicon label
primer label
technical replicate group
nominal direction
~~~

Therefore an unlabeled sample still has complete coordinate and orientation
support topology. Amplicon/primer grouping enriches provenance when supplied but
is not required for reconciliation.

In data models, optional assay grouping should remain visibly optional rather
than being synthesized from filenames.


## Concrete placement handoff from current Signal

The sample layer should not rediscover read coverage.

Current single-read alignment already returns:

~~~text
orientation
reference_segments
wraps_origin
alignment columns
alignment metrics
~~~

These are the authoritative placement facts.

Therefore the handoff should be:

~~~text
QualityControlResult
   ->
align_best(...)
   ->
Alignment
   ->
ReadObservation::from_alignment(...)
~~~

not:

~~~text
filename/HV label
   ->
guess region
   ->
sample-specific aligner
~~~

For a set of unlabeled traces, each `Alignment.reference_segments` determines
which sample coordinates that read can contribute to. Pairing and overlap then
emerge from coordinates rather than file naming.
