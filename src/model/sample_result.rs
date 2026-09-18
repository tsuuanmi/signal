//! Serializable `signal.sample_evidence/v1` contract.

use serde::Serialize;

use crate::model::alignment::Orientation;
use crate::model::result::{IntervalResult, ReferenceResult};
use crate::model::sample_evidence::LocusState;
use crate::model::variant::{VariantCallRole, VariantExclusionReason, VariantKind};

/// Successful sample-evidence document.
#[derive(Debug, Serialize)]
pub(crate) struct SampleEvidenceResult {
    pub(crate) schema_version: &'static str,
    pub(crate) sample_id: String,
    pub(crate) provenance: SampleProvenanceResult,
    pub(crate) reads: Vec<SampleReadResult>,
    pub(crate) loci: Vec<SampleLocusResult>,
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
    pub(crate) alignment: SampleReadAlignmentResult,
}

/// Concise evidence supporting the selected alignment and placement.
#[derive(Debug, Serialize)]
pub(crate) struct SampleReadAlignmentResult {
    pub(crate) orientation: Orientation,
    pub(crate) callable_bases: usize,
    pub(crate) identity: f64,
    pub(crate) mismatches: usize,
    pub(crate) gap_opens: usize,
    pub(crate) unresolved_bases: usize,
    pub(crate) reference_segments: Vec<IntervalResult>,
    pub(crate) wraps_origin: bool,
}

/// Evidence at one covered reference locus.
#[derive(Debug, Serialize)]
pub(crate) struct SampleLocusResult {
    pub(crate) position: usize,
    pub(crate) reference: char,
    pub(crate) observations: Vec<SampleLocusObservationResult>,
}

/// One read's aligned observation at a locus.
#[derive(Debug, Serialize)]
pub(crate) struct SampleLocusObservationResult {
    pub(crate) read_name: String,
    pub(crate) read_sha256: String,
    pub(crate) orientation: Orientation,
    pub(crate) state: LocusState,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) base: Option<char>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) index: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) relative_quality: Option<u8>,
}

/// One normalized observed variant and its supporting reads.
#[derive(Debug, Serialize)]
pub(crate) struct SampleVariantResult {
    pub(crate) position: usize,
    pub(crate) reference: String,
    pub(crate) alternate: String,
    pub(crate) kind: VariantKind,
    pub(crate) support: Vec<SampleVariantSupportResult>,
}

/// One read contributing to a normalized variant.
#[derive(Debug, Serialize)]
pub(crate) struct SampleVariantSupportResult {
    pub(crate) read_name: String,
    pub(crate) read_sha256: String,
    pub(crate) orientation: Orientation,
    pub(crate) eligible: bool,
    pub(crate) exclusion_reasons: Vec<VariantExclusionReason>,
    pub(crate) calls: Vec<SampleVariantCallResult>,
}

/// Concise mapping from a sample variant back to one original trace call.
#[derive(Debug, Serialize)]
pub(crate) struct SampleVariantCallResult {
    pub(crate) role: VariantCallRole,
    pub(crate) index: usize,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) position: Option<usize>,
    pub(crate) ploc: usize,
}
