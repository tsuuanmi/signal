//! Membership of call-backed sample evidence in merged candidate-noisy regions.

use crate::error::{Error, Result};
use crate::model::read_observation::ReadObservation;

/// Returns whether one original call lies inside any merged candidate-noisy region.
pub(super) fn contains_call(read: &ReadObservation, call_index_0based: usize) -> Result<bool> {
    let call_count = read.signal.loci.len();
    if !read
        .signal
        .loci
        .get(call_index_0based)
        .is_some_and(|locus| locus.call_index_0based == call_index_0based)
    {
        return Err(Error::Sample(format!(
            "call index {call_index_0based} lacks matching locus evidence"
        )));
    }

    for region in &read.signal.noisy_regions {
        if region.call_start_0based >= region.call_end_0based_exclusive
            || region.call_end_0based_exclusive > call_count
        {
            return Err(Error::Sample(
                "candidate-noisy region is outside the read call domain".into(),
            ));
        }
    }

    Ok(read.signal.noisy_regions.iter().any(|region| {
        region.call_start_0based <= call_index_0based
            && call_index_0based < region.call_end_0based_exclusive
    }))
}
