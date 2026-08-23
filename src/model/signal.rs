//! Observational signal-quality windows and merged candidate-noisy regions.

/// Signal-quality features for one rolling base-call window.
#[derive(Debug, Clone)]
pub struct SignalWindow {
    pub(crate) call_start_0based: usize,
    pub(crate) call_end_0based_exclusive: usize,
    pub(crate) sample_start_0based: usize,
    pub(crate) sample_end_0based_exclusive: usize,
    pub(crate) minimum_primary_snr: f64,
    pub(crate) maximum_secondary_snr: f64,
    pub(crate) candidate_noisy: bool,
}

/// Union of overlapping or adjacent candidate-noisy windows.
#[derive(Debug, Clone)]
pub struct NoisyRegion {
    pub(crate) call_start_0based: usize,
    pub(crate) call_end_0based_exclusive: usize,
    pub(crate) sample_start_0based: usize,
    pub(crate) sample_end_0based_exclusive: usize,
    pub(crate) minimum_primary_snr: f64,
}

/// Complete observation-only signal analysis.
#[derive(Debug, Clone)]
pub struct SignalAnalysis {
    pub(crate) windows: Vec<SignalWindow>,
    pub(crate) noisy_regions: Vec<NoisyRegion>,
}

impl SignalAnalysis {
    /// Number of rolling windows classified as candidate-noisy.
    pub(crate) fn noisy_window_count(&self) -> usize {
        self.windows
            .iter()
            .filter(|window| window.candidate_noisy)
            .count()
    }

    /// Number of distinct calls covered by merged candidate-noisy regions.
    pub(crate) fn noisy_call_count(&self) -> usize {
        self.noisy_regions
            .iter()
            .map(|region| region.call_end_0based_exclusive - region.call_start_0based)
            .sum()
    }
}
