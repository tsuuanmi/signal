//! Compact serializable `signal.analysis/v3` contract.

use serde::Serialize;

use crate::model::alignment::{AlignmentMetrics, Orientation};
use crate::model::basecalls::PeakSource;
use crate::model::reference::ReferenceTopology;
use crate::model::variant::{VariantCallRole, VariantKind};

/// Successful compact analysis document.
#[derive(Debug, Serialize)]
pub struct AnalysisResult {
    pub(crate) schema_version: &'static str,
    pub(crate) meta: MetaResult,
    pub(crate) sequence: SequenceResult,
    pub(crate) alignment: AlignmentResult,
    pub(crate) variants: Vec<VariantResult>,
    pub(crate) warnings: WarningSummaryResult,
}

/// Minimal deterministic provenance and input identity.
#[derive(Debug, Serialize)]
pub struct MetaResult {
    pub(crate) program: &'static str,
    pub(crate) version: &'static str,
    pub(crate) deterministic: bool,
    pub(crate) input: TraceResult,
    pub(crate) reference: ReferenceResult,
    pub(crate) configuration_sha256: String,
    pub(crate) methods: MethodsResult,
}

/// Trace identity without decoded bulk data.
#[derive(Debug, Serialize)]
pub struct TraceResult {
    pub(crate) file_name: String,
    pub(crate) sha256: String,
}

/// Reference identity used by the selected alignment.
#[derive(Debug, Serialize)]
pub struct ReferenceResult {
    pub(crate) name: String,
    pub(crate) topology: ReferenceTopology,
    pub(crate) sequence_sha256: String,
}

/// Versioned scientific method identifiers.
#[derive(Debug, Serialize)]
pub struct MethodsResult {
    pub(crate) basecalling: &'static str,
    pub(crate) quality_control: &'static str,
    pub(crate) trimming: &'static str,
    pub(crate) alignment: &'static str,
    pub(crate) variant_calling: &'static str,
}

/// Core sequence and trim result.
#[derive(Debug, Serialize)]
pub struct SequenceResult {
    pub(crate) primary: String,
    pub(crate) ambiguity: String,
    pub(crate) retained: String,
    pub(crate) trim: IntervalResult,
}

/// A 0-based half-open interval.
#[derive(Debug, Serialize)]
pub struct IntervalResult {
    pub(crate) start: usize,
    pub(crate) end: usize,
}

/// Selected alignment only; losing orientation candidates are omitted.
#[derive(Debug, Serialize)]
pub struct AlignmentResult {
    pub(crate) orientation: Orientation,
    pub(crate) score: i64,
    pub(crate) metrics: AlignmentMetrics,
    pub(crate) reference_segments: Vec<IntervalResult>,
    pub(crate) wraps_origin: bool,
    pub(crate) operation_runs: String,
    pub(crate) gapped_query: String,
    pub(crate) gapped_reference: String,
}

/// Compact normalized variant with its associated chromatogram calls.
#[derive(Debug, Serialize)]
pub struct VariantResult {
    pub(crate) contig: String,
    pub(crate) position: usize,
    pub(crate) reference: String,
    pub(crate) alternate: String,
    pub(crate) kind: VariantKind,
    pub(crate) classification: &'static str,
    pub(crate) normalization: &'static str,
    pub(crate) calls: Vec<VariantCallResult>,
}

/// One supporting or flanking trace call associated with a variant.
#[derive(Debug, Serialize)]
pub struct VariantCallResult {
    pub(crate) role: VariantCallRole,
    pub(crate) index: usize,
    /// One-based aligned reference position; absent for inserted calls.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) position: Option<usize>,
    pub(crate) ploc: usize,
    pub(crate) primary: char,
    pub(crate) ambiguity: char,
    pub(crate) peaks: ChannelPeaksResult,
    pub(crate) quality: VariantQualityResult,
}

/// A/C/G/T peak evidence for one variant-associated call.
#[derive(Debug, Serialize)]
pub struct ChannelPeaksResult {
    #[serde(rename = "A")]
    pub(crate) a: PeakResult,
    #[serde(rename = "C")]
    pub(crate) c: PeakResult,
    #[serde(rename = "G")]
    pub(crate) g: PeakResult,
    #[serde(rename = "T")]
    pub(crate) t: PeakResult,
}

/// One selected channel peak.
#[derive(Debug, Serialize)]
pub struct PeakResult {
    pub(crate) height: i32,
    pub(crate) position: usize,
    pub(crate) source: PeakSource,
}

/// Relative and optional applicable vendor quality for one call.
#[derive(Debug, Serialize)]
pub struct VariantQualityResult {
    pub(crate) relative_score: u8,
    pub(crate) penalty: i32,
    pub(crate) phred_calibrated: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) vendor_score: Option<u8>,
    pub(crate) vendor_score_applies: bool,
}

/// Counts of non-fatal conditions, replacing verbose per-call messages.
#[derive(Debug, Serialize)]
pub struct WarningSummaryResult {
    pub(crate) total: usize,
    pub(crate) unresolved_primary_calls: usize,
    pub(crate) multi_channel_unresolved_calls: usize,
    pub(crate) vendor_disagreements: usize,
    pub(crate) excluded_variant_candidates: usize,
    pub(crate) reference_origin_wrap: bool,
}
