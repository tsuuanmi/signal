//! Nucleotide contribution eligibility for retained sample-locus observations.

use crate::model::locus_evidence::EvidenceProfile;
use crate::model::sample_evidence::{LocusState, NucleotideContribution};

/// Classifies whether one observation has actual nucleotide evidence for future aggregation.
pub(super) fn classify(
    state: LocusState,
    profile: Option<EvidenceProfile>,
) -> NucleotideContribution {
    if state == LocusState::Deletion {
        NucleotideContribution::DeletionEvent
    } else if profile.is_some() {
        NucleotideContribution::Eligible
    } else {
        NucleotideContribution::MissingProfile
    }
}
