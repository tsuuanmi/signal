//! Read-local continuous mtDNA poly-C phase evidence.

mod geometry;
mod measure;

pub(crate) const WINDOW_PROFILE_OBSERVATIONS: usize = 25;
pub(crate) const WINDOW_STEP_PROFILE_OBSERVATIONS: usize = 5;
pub(crate) const MAX_REFERENCE_OFFSET_IN_READ_ORDER: i8 = 5;
pub(crate) const CANDIDATE_OFFSETS: [i8; 10] = [-5, -4, -3, -2, -1, 1, 2, 3, 4, 5];

pub(crate) use measure::measure;
