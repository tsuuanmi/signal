//! Compact serializable `signal.analysis/v5` contract.

use serde::Serialize;

use crate::model::alignment::Orientation;
use crate::model::reference::ReferenceTopology;
use crate::model::variant::{VariantCallRole, VariantKind};

/// Successful compact analysis document.
#[derive(Debug, Serialize)]
pub struct AnalysisResult {
    pub(crate) schema_version: &'static str,
    pub(crate) provenance: ProvenanceResult,
    pub(crate) read: ReadResult,
    pub(crate) signal_quality: SignalQualityResult,
    pub(crate) alignment: AlignmentResult,
    pub(crate) variants: Vec<VariantResult>,
    pub(crate) warnings: WarningSummaryResult,
}

/// Deterministic identities needed to reproduce an analysis.
#[derive(Debug, Serialize)]
pub struct ProvenanceResult {
    pub(crate) software_version: &'static str,
    pub(crate) input: InputResult,
    pub(crate) reference: ReferenceResult,
    pub(crate) configuration_sha256: String,
}

/// Trace identity without an identifying filename or decoded bulk data.
#[derive(Debug, Serialize)]
pub struct InputResult {
    pub(crate) sha256: String,
}

/// Reference identity used by the selected alignment.
#[derive(Debug, Serialize)]
pub struct ReferenceResult {
    pub(crate) name: String,
    pub(crate) topology: ReferenceTopology,
    pub(crate) sha256: String,
}

/// Call count and retained interval without complete sequence strings.
#[derive(Debug, Serialize)]
pub struct ReadResult {
    pub(crate) call_count: usize,
    pub(crate) trim: IntervalResult,
}

/// A 0-based half-open interval.
#[derive(Debug, Serialize)]
pub struct IntervalResult {
    pub(crate) start: usize,
    pub(crate) end: usize,
}

/// Merged observation-only signal-quality regions.
#[derive(Debug, Serialize)]
pub struct SignalQualityResult {
    pub(crate) noisy_regions: Vec<NoisyRegionResult>,
}

/// A union of overlapping or adjacent candidate-noisy windows.
#[derive(Debug, Serialize)]
pub struct NoisyRegionResult {
    pub(crate) calls: IntervalResult,
    pub(crate) samples: IntervalResult,
    pub(crate) minimum_primary_snr: f64,
}

/// Concise summary of the selected alignment.
#[derive(Debug, Serialize)]
pub struct AlignmentResult {
    pub(crate) orientation: Orientation,
    pub(crate) callable_bases: usize,
    pub(crate) identity: f64,
    pub(crate) unresolved_bases: usize,
    pub(crate) gap_opens: usize,
    pub(crate) reference_segments: Vec<IntervalResult>,
    pub(crate) wraps_origin: bool,
}

/// Compact normalized variant with mapped trace calls.
#[derive(Debug, Serialize)]
pub struct VariantResult {
    pub(crate) position: usize,
    pub(crate) reference: String,
    pub(crate) alternate: String,
    pub(crate) kind: VariantKind,
    pub(crate) calls: Vec<VariantCallResult>,
}

/// One supporting or flanking trace call associated with a variant.
#[derive(Debug, Serialize)]
pub struct VariantCallResult {
    pub(crate) role: VariantCallRole,
    pub(crate) index: usize,
    /// One-based aligned reference position; absent for inserted supporting calls.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) position: Option<usize>,
    pub(crate) ploc: usize,
    pub(crate) primary: char,
    pub(crate) ambiguity: char,
    /// Maximum A/C/G/T peak height; present only for supporting calls.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) maximum_peak_height: Option<i32>,
    /// Uncalibrated relative quality; present only for supporting calls.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) relative_quality: Option<u8>,
}

/// Public non-fatal analysis counts.
#[derive(Debug, Serialize)]
pub struct WarningSummaryResult {
    pub(crate) unresolved_primary_calls: usize,
    pub(crate) multi_channel_unresolved_calls: usize,
    pub(crate) excluded_variant_candidates: usize,
}
