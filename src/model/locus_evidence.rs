//! Basecall-independent signal evidence at one vendor-defined locus.

/// Normalized non-negative A/C/G/T evidence derived from corrected channel amplitudes.
///
/// Channel order follows `Nucleotide::ALL`: A, C, G, T.
#[derive(Debug, Clone, Copy, PartialEq)]
pub(crate) struct EvidenceProfile {
    pub(crate) weights: [f64; 4],
}

/// Immutable signal evidence at one PLOC-defined locus.
///
/// The event sample and profile are derived from channel evidence directly. They
/// do not depend on the primary call, ambiguity code, or qualifying-channel set.
#[derive(Debug, Clone)]
pub(crate) struct LocusEvidence {
    pub(crate) call_index_0based: usize,
    pub(crate) ploc_0based: usize,
    pub(crate) window_start_0based: usize,
    pub(crate) window_end_0based_exclusive: usize,
    pub(crate) context_call_start_0based: usize,
    pub(crate) context_call_end_0based_exclusive: usize,
    pub(crate) context_sample_start_0based: usize,
    pub(crate) context_sample_end_0based_exclusive: usize,
    pub(crate) event_position_0based: usize,
    pub(crate) channel_heights: [i32; 4],
    pub(crate) channel_baselines: [f64; 4],
    pub(crate) channel_noise_sigmas: [f64; 4],
    pub(crate) corrected_amplitudes: [f64; 4],
    pub(crate) snrs: [f64; 4],
    pub(crate) profile: Option<EvidenceProfile>,
}
