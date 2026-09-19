# ADR-0052: Treat post-poly-C evidence as directionally lower-confidence when read phase is unstable

- **Status:** Accepted
- **Date:** 2026-09-20
- **Implementation:** Deferred; this ADR defines the scientific/engineering invariant only.

## Context

Sanger sequencing through long homopolymers can lose phase because polymerase slippage or
mis-annealing produces extension products offset by one or more bases. The resulting
electropherogram can remain mixed or noisy after the homopolymer rather than only inside
the repeat itself.

This is especially relevant to the mtDNA control-region poly-C tracts:

- HV2 around positions 303–315;
- HV1 around positions 16184–16193.

These tracts commonly show length variation/heteroplasmy, and variants that remove an
interrupting thymidine can create a longer uninterrupted C stretch. Published Sanger
guidance and mtDNA studies report degraded or unreadable sequence after such homopolymers.

The local validation corpus shows the same directional pattern. A locus can be supported
cleanly by one read that reaches it before crossing the C stretch while an overlapping
read from the opposite direction reaches the same locus only after crossing the tract and
shows mixed, noisy, or shifted evidence. Therefore reliability cannot be represented by a
genomic-position mask alone.

## Decision

When a read shows evidence that an mtDNA poly-C tract has caused phase instability,
nucleotide and variant evidence **after that tract in sequencing order MUST be treated as
lower-confidence than otherwise equivalent evidence that has not crossed the unstable
tract**.

This is a read-path property, not a locus property.

For a given genomic locus:

- a read that has already crossed an unstable poly-C tract may be confidence-attenuated;
- an overlapping read that reaches the same locus before crossing that tract is not
  attenuated merely because the locus is near or downstream of the tract in reference
  coordinates;
- the rule follows the selected read orientation and actual sequencing path;
- evidence from an affected read MUST NOT outweigh cleaner overlapping evidence solely
  because both reads cover the same locus.

The first implementation of this decision SHOULD be conservative. It may lower confidence
or evidence weight, but MUST NOT automatically reclassify a variant as artifact or remove
the read from the sample.

## What counts as an unstable poly-C tract

This ADR intentionally does not freeze one detector.

Future implementation may use evidence such as:

- length-heteroplasmy or stutter around the tract;
- sustained multi-channel impurity after the tract;
- repeated ±1 phase-shadow signal;
- disagreement with an overlapping read that has not crossed the tract;
- tract structure such as loss of an interrupting base;
- direct phase-recovery evidence later in the read.

The detector and its thresholds require validation and are not production requirements
yet.

## Recovery

Confidence MUST NOT be restored using a hard-coded genomic distance alone.

The effect of homopolymer-induced dephasing can persist for an unknown and
sample/read-specific distance. A future implementation should restore normal confidence
only when the read provides evidence that phase coherence has recovered.

Until a recovery model is validated, downstream evidence from a demonstrably unstable
tract should remain conservatively lower-confidence for review/calling purposes.

## Consequences

- Signal must reason about sequencing history, not only reference coordinate.
- Homopolymer context becomes directional and read-specific.
- The same locus may legitimately carry different confidence on forward and reverse
  reads.
- Clean overlapping evidence from a read that has not crossed the tract becomes
  especially valuable for resolving post-homopolymer observations.
- Recurrent mixed loci after HV1/HV2 C stretches should be studied as possible
  phase-discordant evidence before being promoted to biological heteroplasmy truth.
- Future confidence/scoring work must preserve the distinction between biological
  length heteroplasmy, PCR/cycle-sequencing slippage, and the downstream reliability
  consequence; it need not solve their biological origin before discounting unreliable
  nucleotide evidence.

## Deferred implementation

A later research/implementation change may introduce explicit evidence such as:

- whether the read has crossed a known homopolymer tract;
- tract identity and inferred instability;
- distance from the tract in read order;
- phase-shadow measurements;
- phase-recovery state;
- a validated confidence attenuation model.

Those fields, thresholds, and output contracts are deliberately not defined here.

## Evidence basis

- Thermo Fisher Sanger troubleshooting guidance notes that homopolymers longer than about
  8–9 bases can produce n±1 peaks, mixed sequence, and increased baseline noise after the
  homopolymer:
  <https://www.thermofisher.com/TFS-Assets/LSG/manuals/MAN0014435_Trbleshoot_Sanger_seq_data_UB.pdf>
- Human mtDNA studies describe the HV2 303–315 and HV1 16184–16193 poly-C tracts as
  common length-heteroplasmy regions and report difficulty sequencing beyond extended
  C stretches:
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC3076767/>
- T16189C can create an uninterrupted HV1 poly-C tract with heteroplasmic length
  variation and unreadable sequence beyond the tract:
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC5385546/>

## Non-goals

This ADR does not define a fixed post-poly-C exclusion window, a universal confidence
multiplier, a production threshold, an artifact label, a heteroplasmy verdict, a tract
genotype rule, or an implementation schema. It introduces no production behavior by
itself.
