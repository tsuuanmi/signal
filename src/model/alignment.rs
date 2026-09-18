//! Pairwise alignment records with explicit strand and coordinates.

use serde::Serialize;

/// Query orientation relative to the supplied reference strand.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Orientation {
    /// Native retained query matches the reference strand.
    Forward,
    /// Reverse-complemented retained query matches the reference strand.
    Reverse,
}

/// One half-open segment on the original reference.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ReferenceSegment {
    pub(crate) start_0based: usize,
    pub(crate) end_0based_exclusive: usize,
}

impl ReferenceSegment {
    /// Returns whether this segment overlaps another half-open segment.
    pub(crate) fn overlaps(&self, other: &Self) -> bool {
        self.start_0based < other.end_0based_exclusive
            && other.start_0based < self.end_0based_exclusive
    }
}

/// Alignment quality metrics.
#[derive(Debug, Clone, Serialize)]
pub struct AlignmentMetrics {
    pub(crate) exact_matches: usize,
    pub(crate) mismatches: usize,
    pub(crate) gap_opens: usize,
    pub(crate) callable_columns: usize,
    pub(crate) callable_identity: f64,
    pub(crate) unresolved_query_bases: usize,
}

/// One column of the selected alignment.
#[derive(Debug, Clone)]
pub struct AlignmentColumn {
    pub(crate) query_base: char,
    pub(crate) reference_base: char,
    pub(crate) original_call_index_0based: Option<usize>,
    pub(crate) reference_index_0based: Option<usize>,
}

/// Selected alignment and both orientation summaries.
#[derive(Debug, Clone)]
pub struct Alignment {
    pub(crate) orientation: Orientation,
    pub(crate) score: i64,
    pub(crate) reference_segments: Vec<ReferenceSegment>,
    pub(crate) wraps_origin: bool,
    pub(crate) metrics: AlignmentMetrics,
    pub(crate) columns: Vec<AlignmentColumn>,
}

impl Alignment {
    /// Returns whether two selected placements cover at least one shared
    /// reference coordinate.
    pub(crate) fn overlaps_reference(&self, other: &Self) -> bool {
        self.reference_segments.iter().any(|left| {
            other
                .reference_segments
                .iter()
                .any(|right| left.overlaps(right))
        })
    }
}

#[cfg(test)]
mod tests {
    use super::{Alignment, AlignmentMetrics, Orientation, ReferenceSegment};

    fn alignment(segments: &[(usize, usize)]) -> Alignment {
        Alignment {
            orientation: Orientation::Forward,
            score: 0,
            reference_segments: segments
                .iter()
                .map(|&(start_0based, end_0based_exclusive)| ReferenceSegment {
                    start_0based,
                    end_0based_exclusive,
                })
                .collect(),
            wraps_origin: segments.len() > 1,
            metrics: AlignmentMetrics {
                exact_matches: 0,
                mismatches: 0,
                gap_opens: 0,
                callable_columns: 0,
                callable_identity: 0.0,
                unresolved_query_bases: 0,
            },
            columns: Vec::new(),
        }
    }

    #[test]
    fn detects_linear_reference_overlap() {
        assert!(alignment(&[(100, 200)]).overlaps_reference(&alignment(&[(150, 250)])));
    }

    #[test]
    fn touching_half_open_segments_do_not_overlap() {
        assert!(!alignment(&[(100, 200)]).overlaps_reference(&alignment(&[(200, 250)])));
    }

    #[test]
    fn detects_overlap_across_circular_origin_segments() {
        assert!(alignment(&[(16_500, 16_569), (0, 120)])
            .overlaps_reference(&alignment(&[(80, 300)])));
    }
}
