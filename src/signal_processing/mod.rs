//! Observation-only rolling signal-quality analysis.

mod call_metrics;
mod features;
mod regions;
mod statistics;

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
    let call_metrics = call_metrics::calculate(trace, calls, &windows, config)?;
    let noisy_regions = regions::merge(&windows, config.minimum_noisy_windows);
    Ok(SignalAnalysis {
        call_metrics,
        windows,
        noisy_regions,
    })
}
