//! Compact sample evidence aggregated across independently processed reads.

use serde::Serialize;

use crate::model::alignment::{Orientation, ReferenceSegment};
use crate::model::signal::TraceIntegrity;
use crate::model::variant::{VariantCallRole, VariantExclusionReason, VariantKind};

/// Why a mapped read pair is not admitted as reliable overlap evidence.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum OverlapExclusionReason {
    ComparableBasesBelowMinimum,
    AgreementBelowMinimum,
}

/// Pairwise overlap evidence discovered after independent reference placement.
#[derive(Debug, Clone)]
pub(crate) struct ReadOverlapEvidence {
    pub(crate) left_read_index: usize,
    pub(crate) right_read_index: usize,
    pub(crate) shared_positions: usize,
    pub(crate) comparable_bases: usize,
    pub(crate) agreements: usize,
    pub(crate) conflicts: usize,
    pub(crate) agreement: Option<f64>,
    pub(crate) eligible: bool,
    pub(crate) exclusion_reasons: Vec<OverlapExclusionReason>,
}

/// How one read observes a locus retained because at least one read differs.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum LocusState {
    Reference,
    Alternate,
    Unresolved,
    Deletion,
}

/// Concise evidence supporting one selected read placement.
#[derive(Debug, Clone)]
pub(crate) struct SampleReadAlignmentEvidence {
    pub(crate) orientation: Orientation,
    pub(crate) callable_bases: usize,
    pub(crate) identity: f64,
    pub(crate) gap_opens: usize,
    pub(crate) unresolved_bases: usize,
    pub(crate) reference_segments: Vec<ReferenceSegment>,
    pub(crate) wraps_origin: bool,
}

/// One read retained once at sample scope.
#[derive(Debug, Clone)]
pub(crate) struct SampleReadEvidence {
    pub(crate) input_name: String,
    pub(crate) input_sha256: String,
    pub(crate) integrity: TraceIntegrity,
    pub(crate) alignment: SampleReadAlignmentEvidence,
}

/// One observation at a covered locus retained because the sample differs there.
#[derive(Debug, Clone)]
pub(crate) struct LocusDifferenceObservation {
    pub(crate) read_index: usize,
    pub(crate) state: LocusState,
    pub(crate) base: Option<char>,
    pub(crate) quality: Option<u8>,
}

/// All covering-read observations retained at one differential reference locus.
#[derive(Debug, Clone)]
pub(crate) struct LocusDifferenceEvidence {
    pub(crate) position_1based: usize,
    pub(crate) reference_base: char,
    pub(crate) observations: Vec<LocusDifferenceObservation>,
}

/// One trace call directly supporting or flanking a normalized variant.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct VariantCallEvidence {
    pub(crate) role: VariantCallRole,
    pub(crate) base: char,
    pub(crate) peak_heights: [i32; 4],
    pub(crate) quality: u8,
}

/// One read observing a normalized variant, with configured eligibility retained.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct VariantSupport {
    pub(crate) read_index: usize,
    pub(crate) eligible: bool,
    pub(crate) exclusion_reasons: Vec<VariantExclusionReason>,
    pub(crate) calls: Vec<VariantCallEvidence>,
}

/// One normalized observed variant with factorized read support.
#[derive(Debug, Clone)]
pub(crate) struct VariantEvidence {
    pub(crate) position_1based: usize,
    pub(crate) reference: String,
    pub(crate) alternate: String,
    pub(crate) kind: VariantKind,
    pub(crate) support: Vec<VariantSupport>,
}

/// Complete compact evidence for one sample.
#[derive(Debug, Clone)]
pub(crate) struct SampleEvidence {
    pub(crate) reference_sha256: String,
    pub(crate) configuration_sha256: String,
    pub(crate) reads: Vec<SampleReadEvidence>,
    pub(crate) overlaps: Vec<ReadOverlapEvidence>,
    pub(crate) locus_differences: Vec<LocusDifferenceEvidence>,
    pub(crate) variants: Vec<VariantEvidence>,
}
