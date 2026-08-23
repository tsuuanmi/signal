//! Affine scoring and deterministic state ordering.

use crate::config::AlignmentConfig;

pub(crate) const NEGATIVE_INFINITY: i64 = i64::MIN / 4;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum State {
    Match = 0,
    Insertion = 1,
    Deletion = 2,
}

impl State {
    pub(crate) const fn from_bits(bits: u8) -> Self {
        match bits {
            1 => Self::Insertion,
            2 => Self::Deletion,
            _ => Self::Match,
        }
    }
}

pub(crate) fn substitution(query: u8, reference: u8, config: &AlignmentConfig) -> i64 {
    let score = if is_canonical(query) && is_canonical(reference) {
        if query == reference {
            config.match_score
        } else {
            config.mismatch_score
        }
    } else {
        config.ambiguous_score
    };
    i64::from(score)
}

pub(crate) const fn is_canonical(base: u8) -> bool {
    matches!(base, b'A' | b'C' | b'G' | b'T')
}

pub(crate) fn add(score: i64, delta: i64) -> i64 {
    if score <= NEGATIVE_INFINITY / 2 {
        NEGATIVE_INFINITY
    } else {
        score + delta
    }
}
