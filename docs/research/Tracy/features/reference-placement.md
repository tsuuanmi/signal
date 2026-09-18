# Reference Placement and Search

Tracy separates two problems that are easy to conflate:

~~~text
Where in a large reference might this trace belong?
~~~

and

~~~text
What is the best scientific alignment once the candidate region is known?
~~~

This distinction matters less for Signal's current <=50 kb reference scope, but
it is a useful architectural lesson if reference scope grows later.

## Tracy's two placement modes

For a small single-record FASTA, Tracy performs direct trace-profile-to-sequence
dynamic programming. This is relatively sensitive because the full profile
evidence participates in alignment.

For an indexed large reference, Tracy first performs seed search:

1. use the trace consensus string;
2. scan exact k-mers (default k=15);
3. initially prefer k-mers that occur exactly once;
4. convert each seed hit into an inferred trace start coordinate;
5. choose the coordinate with the largest supporting hit count;
6. require minimum k-mer support;
7. require one orientation to have more than twice the support of the other;
8. if unique seeds fail, retry with non-unique hits occurring fewer than 1000 times;
9. extract a local reference slice around the inferred coordinate;
10. run profile-to-sequence alignment on that slice.

The seed stage is therefore a **candidate locator**, not the final scientific alignment.

## Sensitivity tradeoff

Tracy's maintainer explicitly notes in issues #15 and #34 that index-based
search is faster but less sensitive than direct profile-to-sequence alignment.

Exact seeding becomes fragile when:

- the trace contains many `N` calls;
- primary calls are wrong;
- usable sequence is short after trimming;
- the locus is repetitive;
- a variant/indel disrupts several neighboring seeds.

This is a speed/sensitivity tradeoff, not an alignment-quality statement.

## Circular topology exposes the boundary

Issue #41 is especially informative. Tracy's indexed and unindexed paths
produced different behavior for a circular viral genome because both placement
and final profile alignment assumed a linear reference. The indexed path found
a seed near the reference end but could not represent continuation at the
reference start.

Signal already models circular topology explicitly. Any future placement layer
must preserve that topology instead of forcing circular data into one linear
candidate coordinate.

## Signal design

Signal does not currently need FM-index placement for mtDNA-sized references.
The present bounded direct Gotoh alignment is simpler and more auditable.

If large-reference search is ever introduced, use a layered contract:

~~~text
query evidence
    |
    v
candidate placement search
    |
    +--> CandidateRegion 1
    +--> CandidateRegion 2
    +--> ...
             |
             v
authoritative evidence-aware alignment
             |
             v
selected or ambiguous placement
~~~

The search stage may optimize speed but must not become the scientific truth source.

## Candidate placement contract

A future placement result should retain:

- candidate reference/contig identity;
- candidate interval;
- orientation;
- seed/support count or search score;
- search method/version;
- whether uniqueness was required;
- topology assumptions;
- enough information to reproduce candidate generation.

It should **not** itself assign final alignment identity, final variant
coordinates, genotype, consensus, or biological correctness.

## Ambiguous placement

Multiple candidate regions with similar evidence should remain explicit.

Do not silently resolve repeats by iteration order, first index hit, reference
file order, lexical contig name, or one arbitrary orientation tie.

The authoritative alignment layer may resolve candidates only under a documented
scoring and tie policy. Otherwise placement is ambiguous.

## Reference ambiguity

Current Tracy replaces IUPAC-degenerate reference bases with `N` before
alignment/indexing and rejects gaps/non-IUPAC characters.

Signal's current production contract is already stricter: one A/C/G/T/N FASTA
record. That is appropriate for now.

If Signal later accepts richer reference ambiguity, its semantics should be
defined explicitly in the alignment scorer rather than silently normalized by
the parser.

## Wild-type AB1 as reference

Tracy can also use a wild-type chromatogram as the reference. Internally it
basecalls that trace, constructs a trace profile, and compares query profile to
wild-type profile.

This is useful in assay/control workflows because it can preserve systematic
instrument/chemistry context shared by the control and sample.

For Signal it should remain a separate future mode, not a replacement for
canonical FASTA/rCRS analysis. A wild-type trace is an **observation**, not an
authoritative coordinate reference unless the assay contract explicitly says so.

## Recommendation

For current Signal:

~~~text
keep direct bounded alignment
keep circular topology
defer FM-index/search
~~~

For future scaling:

~~~text
candidate search != final alignment
reference guidance != observed sample evidence
topology belongs in both placement and alignment contracts
~~~


## Assay metadata must not become the default placement prior

For current mtDNA analysis, the complete circular reference is small enough that
Signal should discover the read placement from the read evidence itself.

Do not use a filename or declared amplicon such as HV2 as an implicit instruction
to search only an HV2 slice.

Optional assay metadata belongs after mapping:

~~~text
read evidence -> authoritative placement -> metadata consistency QC
~~~

not before:

~~~text
metadata -> restricted placement -> apparent confirmation
~~~

If large-reference scaling later makes unrestricted search expensive, any
metadata-assisted candidate restriction must be opt-in, explicit in method
provenance, and validated against an unrestricted/search-based placement path.


## How Tracy actually discovers a read's covered region

This section records the implementation mechanics, not only the architectural
idea. It is the key reference for implementing self-locating reads correctly in
Signal.

### Short reference: direct semi-global profile alignment

For a single FASTA up to 50 kb, `tracy align` does **not** need an amplicon
name, primer name, expected interval, or declared F/R orientation.

The path in `src/sage.h` is:

~~~text
AB1
  -> basecall()
  -> trim
  -> createProfile(trimmed trace)
  -> create forward reference profile
  -> create reverse-complement reference profile
  -> score trace against both orientations
  -> select orientation
  -> semi-global Gotoh alignment
  -> derive the aligned reference slice
~~~

The critical alignment configuration is:

~~~cpp
AlignConfig<true, false> semiglobal;
~~~

In Tracy's Gotoh implementation, the first template flag makes horizontal gaps
free at the beginning and end of the first sequence's DP traversal. With the
trace as the first alignment argument and reference as the second, this means
unmatched **reference flanks** do not cost score.

Conceptually:

~~~text
reference:  NNNNNNNN A C G T T A C G NNNNNNN
                    | | | | | | | |
trace:              A C G T T A C G
~~~

The trace must be consumed, but it can begin and end anywhere inside the
reference. Therefore the traceback itself identifies the covered reference
interval.

This is the mechanism that makes the read self-locating.

### How Tracy chooses orientation on a short reference

Tracy constructs:

~~~text
reference_forward_profile
reference_reverse_complement_profile
~~~

and computes:

~~~text
score_forward = gotohScore(trace_profile, reference_forward_profile)
score_reverse = gotohScore(trace_profile, reference_reverse_profile)
~~~

It then uses the better score to choose the reference orientation and performs
the full semi-global alignment against that profile.

Implementation detail: in `sage.h`, an exact score tie falls into the reverse
branch because the code tests `gsFwd > gsRev`. This is a deterministic
implementation artifact, not a biological rule and should **not** be copied by
Signal.

### How Tracy converts the alignment into a reference span

After the preliminary alignment, Tracy calls `trimReferenceSlice()`.

That function:

1. finds the first and last alignment columns containing trace/query bases;
2. counts how many reference bases occur before the aligned trace;
3. counts the reference span covered while the trace is present;
4. extends that reference slice by the trace's left/right trim amounts where
   bounds allow;
5. updates the reference start coordinate;
6. rebuilds a profile for the resulting local reference slice.

Tracy then aligns the **full trace profile** against that refined reference
profile for its final output.

So for short references, Tracy's logical placement result is not inferred from
the filename. It comes from:

~~~text
semi-global traceback
    ->
first/last query-supported alignment columns
    ->
reference start/span
~~~

### Reference-guided multi-trace assembly

`tracy assemble -r reference.fa ...` uses the same general principle for every
input trace independently.

For each trace:

~~~text
decode
 -> basecall
 -> trim
 -> create trace profile

score(trace_profile, full_reference_profile)
score(reverse_complement(trace_profile), full_reference_profile)

 -> choose better orientation
 -> apply reference-match admission threshold
 -> retain oriented trace profile
~~~

The default reference-match threshold is derived from the trimmed trace length
`L`, configured match fraction `f`, and substitution scores:

~~~text
threshold =
    L * f       * match_score
  + L * (1 - f) * mismatch_score
~~~

The trace is admitted if either orientation scores above that threshold.

Implementation detail: `assemble.h` uses `gsFwd >= gsRev`, so an exact tie is
called forward. This differs from `sage.h`, where a tie selects reverse. Signal
must not inherit either hidden tie policy.

After admission, Tracy sorts reads by best reference score, aligns the
highest-scoring read to the whole reference, and progressively aligns later
reads to the growing MSA profile.

That progressive MSA implicitly contains each read's coverage through its
non-gap columns relative to the reference row.

### Why Signal should stop before Tracy's progressive merge

For Signal, the stronger design is to materialize every read placement **before**
sample reconciliation:

~~~text
trace
 -> authoritative single-read alignment
 -> orientation
 -> reference_segments
 -> alignment columns
 -> ReadObservation
~~~

Then sample merging is only coordinate/event aggregation.

This avoids making the placement of a later read depend on an already-growing
sample MSA.

### Pairwise Tracy consensus is not genomic placement

`tracy consensus trace1 trace2` is different.

It uses:

~~~cpp
AlignConfig<true, true>
~~~

which makes both ends free for an overlap-style alignment. Tracy fixes trace 1
as the relative frame, tests trace 2 forward/reverse, and accepts the overlap
only when:

~~~text
aligned overlap >= 25 bases          # default
primary-character match fraction >= 0.5
~~~

This tells Tracy how two traces overlap **relative to each other**. It does not
tell which mtDNA coordinates they cover because no genomic reference is present.

Therefore Signal should use reference-based independent placement for sample
analysis, not pairwise F/R consensus as the coordinate-discovery mechanism.

### Indexed large-reference path

For an indexed large genome Tracy cannot afford direct DP against the full
reference, so `getReferenceSlice()` first anchors the trace using its basecall
consensus string.

For both forward and reverse-complement consensus:

1. slide exact k-mers (default 15 bp);
2. skip k-mers containing `N`;
3. first keep only k-mers occurring exactly once;
4. for each reference hit at location `h` from query offset `k`, record
   candidate query start `h - k`;
5. choose the most frequent candidate start;
6. require at least `minKmerSupport` hits (default 3);
7. require the winning orientation to have more than 2x the support of the
   opposite orientation;
8. if this fails, retry with non-unique k-mers occurring fewer than 1000 times;
9. build a local reference slice around the winning start, expanded by
   `maxindel`;
10. run the profile alignment on that slice.

This path separates:

~~~text
seed-based candidate location
        !=
final profile alignment
~~~

For mtDNA-sized Signal references, the seed stage is unnecessary.

## Signal already implements the essential short-reference mechanism

Current Signal's production alignment core already has the right primitives.

### Free reference flanks

In `src/alignment/gotoh.rs`:

- the DP row for zero consumed query bases starts with score 0 across all
  reference columns;
- after all query bases are consumed, every reference endpoint is considered;
- therefore the query can start and end anywhere in the reference without
  paying for unused reference flanks.

That is the same scientific placement idea as Tracy's short-reference
semi-global alignment.

### Exact span extraction

`traceback::decode()` starts at:

~~~text
row = query length
column = selected reference endpoint
~~~

and traces backward until all query bases are consumed.

It records:

~~~text
end_reference   = selected endpoint
start_reference = reference column when query traceback reaches row 0
~~~

so Signal already obtains the mapped half-open interval:

~~~text
[start_reference, end_reference)
~~~

from alignment evidence.

### Orientation

`align_best()` creates:

~~~text
forward query
reverse-complement query
~~~

and aligns both against the same reference representation.

It compares candidates using:

1. alignment score;
2. exact matches;
3. fewer mismatches;
4. fewer gap opens.

If the two orientations remain equally supported, Signal returns an explicit
alignment error instead of inventing an F/R answer.

This is stricter and more biologically honest than Tracy's inconsistent
forward/reverse tie defaults.

### Circular mtDNA

For circular references Signal aligns against:

~~~text
reference + reference
~~~

while bounding one alignment to at most one original reference length.

The selected interval is projected modulo the original length into one or two
`ReferenceSegment` values.

Therefore a read crossing the rCRS origin can naturally produce:

~~~text
segment 1: [start, reference_length)
segment 2: [0, end)
wraps_origin = true
~~~

No HV label or manual reference rotation is required.

## Implementation consequence for sample analysis

The first sample-level implementation does **not** need a new algorithm that
guesses whether a file is HV1/HV2/HV3.

It should reuse the authoritative single-read alignment and promote its result
into an immutable read object:

~~~rust
struct ReadObservation {
    read_id: ReadId,

    // Existing alignment-derived facts.
    orientation: Orientation,
    reference_segments: Vec<ReferenceSegment>,
    wraps_origin: bool,
    alignment_columns: Vec<AlignmentColumn>,
    alignment_metrics: AlignmentMetrics,

    // Original trace/call evidence and optional declared metadata.
    // ...
}
~~~

Then overlap is derived mechanically:

~~~text
two reads overlap
iff
their mapped reference segments/events overlap
~~~

For indels, aggregation must use normalized event identity rather than only
interval overlap.

This is the implementation path that preserves Tracy's useful self-placement
mechanism while retaining Signal's stronger tie, circular-topology, and
provenance semantics.
