//! Reference-coordinate evidence aggregated across independently processed reads.

use serde::Serialize;

use crate::model::alignment::{Orientation, ReferenceSegment};
use crate::model::variant::{VariantCallRole, VariantExclusionReason, VariantKind};

/// How one aligned read observes one reference locus.
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
    pub(crate) score: i64,
    pub(crate) callable_bases: usize,
    pub(crate) identity: f64,
    pub(crate) mismatches: usize,
    pub(crate) gap_opens: usize,
    pub(crate) unresolved_bases: usize,
    pub(crate) reference_segments: Vec<ReferenceSegment>,
    pub(crate) wraps_origin: bool,
}

/// One read retained in sample evidence.
#[derive(Debug, Clone)]
pub(crate) struct SampleReadEvidence {
    pub(crate) input_name: String,
    pub(crate) input_sha256: String,
    pub(crate) alignment: SampleReadAlignmentEvidence,
}

/// One aligned observation at a reference locus.
#[derive(Debug, Clone)]
pub(crate) struct LocusObservation {
    pub(crate) input_name: String,
    pub(crate) input_sha256: String,
    pub(crate) orientation: Orientation,
    pub(crate) state: LocusState,
    pub(crate) base: Option<char>,
    pub(crate) call_index_0based: Option<usize>,
    pub(crate) relative_quality: Option<u8>,
}

/// All read observations covering one reference locus.
#[derive(Debug, Clone)]
pub(crate) struct LocusEvidence {
    pub(crate) position_1based: usize,
    pub(crate) reference_base: char,
    pub(crate) observations: Vec<LocusObservation>,
}

/// One trace call directly supporting or flanking a normalized variant.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct VariantCallEvidence {
    pub(crate) role: VariantCallRole,
    pub(crate) call_index_0based: usize,
    pub(crate) reference_position_1based: Option<usize>,
    pub(crate) ploc_0based: usize,
}

/// One read observing a normalized variant, with configured eligibility retained.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct VariantSupport {
    pub(crate) input_name: String,
    pub(crate) input_sha256: String,
    pub(crate) orientation: Orientation,
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

/// Complete reference-coordinate evidence for one sample.
#[derive(Debug, Clone)]
pub(crate) struct SampleEvidence {
    pub(crate) reference_sha256: String,
    pub(crate) configuration_sha256: String,
    pub(crate) reads: Vec<SampleReadEvidence>,
    pub(crate) loci: Vec<LocusEvidence>,
    pub(crate) variants: Vec<VariantEvidence>,
}
