//! Shared projection of merged observational signal-quality regions.

use crate::model::result::{IntervalResult, NoisyRegionResult, SignalQualityResult};
use crate::model::signal::SignalAnalysis;

/// Projects merged noisy regions while omitting internal rolling windows.
pub(super) fn project(signal: SignalAnalysis) -> SignalQualityResult {
    let noisy_regions = signal
        .noisy_regions
        .into_iter()
        .map(|region| NoisyRegionResult {
            calls: IntervalResult {
                start: region.call_start_0based,
                end: region.call_end_0based_exclusive,
            },
            samples: IntervalResult {
                start: region.sample_start_0based,
                end: region.sample_end_0based_exclusive,
            },
            minimum_primary_snr: region.minimum_primary_snr,
        })
        .collect();
    SignalQualityResult { noisy_regions }
}
