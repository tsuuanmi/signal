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
