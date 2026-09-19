//! Projection of existing call-coordinate noisy-region context into sample evidence.

use crate::model::read_observation::ReadObservation;

/// Returns whether one source call falls inside an observation-only merged noisy region.
pub(super) fn for_call(read: &ReadObservation, call_index_0based: usize) -> bool {
    read.signal.noisy_regions.iter().any(|region| {
        region.call_start_0based <= call_index_0based
            && call_index_0based < region.call_end_0based_exclusive
    })
}
