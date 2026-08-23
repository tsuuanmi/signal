//! Observation-only rolling signal-quality analysis.

mod features;
mod regions;

use crate::config::SignalProcessingConfig;
use crate::error::Result;
use crate::model::basecalls::BaseCalls;
use crate::model::signal::SignalAnalysis;
use crate::model::trace::Chromatogram;

/// Calculates rolling SNR features and merged candidate-noisy intervals.
pub(crate) fn analyze(
    trace: &Chromatogram,
    calls: &BaseCalls,
    config: &SignalProcessingConfig,
) -> Result<SignalAnalysis> {
    let windows = features::calculate(trace, calls, config)?;
    let noisy_regions = regions::merge(&windows, config.minimum_noisy_windows);
    Ok(SignalAnalysis {
        windows,
        noisy_regions,
    })
}
