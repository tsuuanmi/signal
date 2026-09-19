//! Observation-only rolling signal-quality analysis.

mod features;
mod locus_evidence;
mod regions;
mod statistics;

use crate::config::SignalProcessingConfig;
use crate::error::Result;
use crate::model::basecalls::BaseCalls;
use crate::model::signal::SignalAnalysis;
use crate::model::trace::Chromatogram;

/// Calculates rolling SNR features, basecall-independent locus evidence, and merged noisy regions.
pub(crate) fn analyze(
    trace: &Chromatogram,
    calls: &BaseCalls,
    config: &SignalProcessingConfig,
) -> Result<SignalAnalysis> {
    let windows = features::calculate(trace, calls, config)?;
    let loci = locus_evidence::calculate(trace, &windows, config)?;
    let noisy_regions = regions::merge(&windows, config.minimum_noisy_windows);
    Ok(SignalAnalysis {
        loci,
        windows,
        noisy_regions,
    })
}
