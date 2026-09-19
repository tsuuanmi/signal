//! Sample-level evidence aggregation in reference-coordinate and variant space.

mod aggregate;
mod call_evidence;
mod contribution;
mod coverage;
mod loci;
mod nucleotide_support;
mod overlap;
mod profile_geometry;
mod variants;

pub(crate) use aggregate::aggregate;

use crate::error::Result;
use crate::model::read_observation::ReadObservation;
use crate::model::sample_evidence::SampleLocusEvidence;

pub(crate) fn all_covered_loci(reads: &[ReadObservation]) -> Result<Vec<SampleLocusEvidence>> {
    let ordered = aggregate::validated_ordered_reads(reads)?;
    loci::aggregate(&ordered, loci::LocusSelection::AllCovered)
}
