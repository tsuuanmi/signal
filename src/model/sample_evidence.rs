//! Reference-coordinate evidence aggregated across independently processed reads.

use serde::Serialize;

use crate::model::alignment::{Orientation, ReferenceSegment};
use crate::model::variant::VariantKind;

/// How one aligned read observes one reference locus.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum LocusState {
    Reference,
    Alternate,
    Unresolved,
    Deletion,
}

/// One read placement retained in sample evidence.
#[derive(Debug, Clone)]
pub(crate) struct SampleReadEvidence {
    pub(crate) input_sha256: String,
    pub(crate) orientation: Orientation,
    pub(crate) reference_segments: Vec<ReferenceSegment>,
    pub(crate) wraps_origin: bool,
}

/// One aligned observation at a reference locus.
#[derive(Debug, Clone)]
pub(crate) struct LocusObservation {
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

/// One read supporting a normalized reportable variant event.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) struct EventSupport {
    pub(crate) input_sha256: String,
    pub(crate) orientation: Orientation,
}

/// One normalized variant event with factorized read support.
#[derive(Debug, Clone)]
pub(crate) struct EventEvidence {
    pub(crate) position_1based: usize,
    pub(crate) reference: String,
    pub(crate) alternate: String,
    pub(crate) kind: VariantKind,
    pub(crate) support: Vec<EventSupport>,
}

/// Complete reference-coordinate evidence for one sample.
#[derive(Debug, Clone)]
pub(crate) struct SampleEvidence {
    pub(crate) reference_sha256: String,
    pub(crate) configuration_sha256: String,
    pub(crate) reads: Vec<SampleReadEvidence>,
    pub(crate) loci: Vec<LocusEvidence>,
    pub(crate) events: Vec<EventEvidence>,
}
