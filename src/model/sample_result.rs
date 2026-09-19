//! Serializable `signal.sample_evidence/v7` contract.

use serde::Serialize;

use crate::model::result::{
    AlignmentResult, PeakHeightsResult, ReferenceResult, TraceIntegrityResult,
};
use crate::model::sample_evidence::{LocusState, OverlapExclusionReason};
use crate::model::variant::{VariantCallRole, VariantExclusionReason, VariantKind};

/// Successful compact sample-evidence document.
#[derive(Debug, Serialize)]
pub(crate) struct SampleEvidenceResult {
    pub(crate) schema_version: &'static str,
    pub(crate) sample_id: String,
    pub(crate) provenance: SampleProvenanceResult,
    pub(crate) reads: Vec<SampleReadResult>,
    pub(crate) coverage: Vec<SampleCoverageResult>,
    pub(crate) overlaps: Vec<SampleOverlapResult>,
    pub(crate) locus_differences: Vec<SampleLocusDifferenceResult>,
    pub(crate) variants: Vec<SampleVariantResult>,
}

/// Scientific identities shared by every sample read.
#[derive(Debug, Serialize)]
pub(crate) struct SampleProvenanceResult {
    pub(crate) reference: ReferenceResult,
    pub(crate) configuration_sha256: String,
}

/// One independently processed sample read with reviewer-facing provenance.
#[derive(Debug, Serialize)]
pub(crate) struct SampleReadResult {
    pub(crate) name: String,
    pub(crate) sha256: String,
    pub(crate) integrity: TraceIntegrityResult,
    pub(crate) alignment: AlignmentResult,
}

/// One maximal reference interval with constant read/orientation depth.
#[derive(Debug, Serialize)]
pub(crate) struct SampleCoverageResult {
    pub(crate) reference: crate::model::result::IntervalResult,
    pub(crate) read_depth: usize,
    pub(crate) forward_depth: usize,
    pub(crate) reverse_depth: usize,
}

/// Pairwise overlap evidence discovered from independently placed reads.
#[derive(Debug, Serialize)]
pub(crate) struct SampleOverlapResult {
    pub(crate) left: String,
    pub(crate) right: String,
    pub(crate) shared_positions: usize,
    pub(crate) comparable_bases: usize,
    pub(crate) agreements: usize,
    pub(crate) conflicts: usize,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) agreement: Option<f64>,
    pub(crate) eligible: bool,
    pub(crate) exclusion_reasons: Vec<OverlapExclusionReason>,
}

/// Evidence at one locus retained because at least one covering read differs.
#[derive(Debug, Serialize)]
pub(crate) struct SampleLocusDifferenceResult {
    pub(crate) position: usize,
    pub(crate) reference: char,
    pub(crate) observations: Vec<SampleLocusDifferenceObservationResult>,
}

/// One covering read's observation at a differential locus.
#[derive(Debug, Serialize)]
pub(crate) struct SampleLocusDifferenceObservationResult {
    pub(crate) read: String,
    pub(crate) state: LocusState,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) base: Option<char>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) quality: Option<u8>,
}

/// One normalized observed variant and its supporting reads.
#[derive(Debug, Serialize)]
pub(crate) struct SampleVariantResult {
    pub(crate) position: usize,
    pub(crate) reference: String,
    pub(crate) alternate: String,
    pub(crate) kind: VariantKind,
    pub(crate) support_topology: SampleVariantSupportTopologyResult,
    pub(crate) support: Vec<SampleVariantSupportResult>,
}

/// Factorized read/orientation topology for one observed normalized variant.
#[derive(Debug, Serialize)]
pub(crate) struct SampleVariantSupportTopologyResult {
    pub(crate) reads: usize,
    pub(crate) eligible_reads: usize,
    pub(crate) forward_reads: usize,
    pub(crate) reverse_reads: usize,
    pub(crate) eligible_forward_reads: usize,
    pub(crate) eligible_reverse_reads: usize,
}

/// One read contributing to a normalized variant.
#[derive(Debug, Serialize)]
pub(crate) struct SampleVariantSupportResult {
    pub(crate) read: String,
    pub(crate) eligible: bool,
    pub(crate) exclusion_reasons: Vec<VariantExclusionReason>,
    pub(crate) calls: Vec<SampleVariantCallResult>,
}

/// Concise mapping from a sample variant back to one original trace call.
#[derive(Debug, Serialize)]
pub(crate) struct SampleVariantCallResult {
    pub(crate) role: VariantCallRole,
    pub(crate) base: char,
    pub(crate) peaks: PeakHeightsResult,
    pub(crate) quality: u8,
}
