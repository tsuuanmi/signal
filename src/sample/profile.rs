//! Reference-oriented projection of basecall-independent call evidence.

use crate::error::{Error, Result};
use crate::model::alignment::Orientation;
use crate::model::locus_evidence::EvidenceProfile;
use crate::model::read_observation::ReadObservation;

/// Returns one call's evidence profile projected onto the selected reference strand.
pub(super) fn for_call(
    read: &ReadObservation,
    call_index_0based: usize,
) -> Result<Option<EvidenceProfile>> {
    let locus = read
        .signal
        .loci
        .get(call_index_0based)
        .filter(|locus| locus.call_index_0based == call_index_0based)
        .ok_or_else(|| {
            Error::Sample(format!(
                "call index {call_index_0based} lacks matching locus evidence"
            ))
        })?;

    Ok(locus.profile.map(|profile| match read.alignment.orientation {
        Orientation::Forward => profile,
        Orientation::Reverse => profile.complemented(),
    }))
}
