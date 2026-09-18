//! Complete scientific observation produced from one independently processed read.

use crate::model::alignment::Alignment;
use crate::model::basecalls::BaseCalls;
use crate::model::quality::QualityControlResult;
use crate::model::signal::SignalAnalysis;
use crate::model::variant::VariantCallingResult;

/// Immutable read-level products after evidence-driven reference placement.
///
/// This is the boundary between one-read processing and future sample-level
/// reconciliation. Placement is already derived from alignment evidence; assay
/// labels or filenames are not part of this scientific observation.
#[derive(Debug, Clone)]
pub(crate) struct ReadObservation {
    pub(crate) input_sha256: String,
    pub(crate) reference_sha256: String,
    pub(crate) configuration_sha256: String,
    pub(crate) calls: BaseCalls,
    pub(crate) signal: SignalAnalysis,
    pub(crate) quality: QualityControlResult,
    pub(crate) alignment: Alignment,
    pub(crate) variants: VariantCallingResult,
}

impl ReadObservation {
    /// Returns whether another read is scientifically comparable for sample
    /// reconciliation under the same reference and scientific configuration.
    pub(crate) fn is_compatible_with(&self, other: &Self) -> bool {
        self.reference_sha256 == other.reference_sha256
            && self.configuration_sha256 == other.configuration_sha256
    }

    /// Returns whether two compatible reads cover at least one shared reference
    /// coordinate. Incompatible reads never overlap scientifically.
    pub(crate) fn overlaps_reference(&self, other: &Self) -> bool {
        self.is_compatible_with(other) && self.alignment.overlaps_reference(&other.alignment)
    }
}
