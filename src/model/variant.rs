//! Normalized primary-sequence differences and original-call mappings.

use serde::Serialize;

/// Supported primary-difference type.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum VariantKind {
    /// Single-nucleotide substitution.
    Snv,
    /// Insertion relative to the reference.
    Ins,
    /// Deletion relative to the reference.
    Del,
}

/// How an original trace call relates to a reported difference.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum VariantCallRole {
    /// A query call directly contributes an observed alternate base.
    Supporting,
    /// A reference-aligned query call bounds an indel.
    Flanking,
}

/// Mapping from a variant-associated call to the selected alignment.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct VariantCallMapping {
    pub(crate) role: VariantCallRole,
    pub(crate) call_index_0based: usize,
    /// Absent only for inserted query calls, which have no reference base.
    pub(crate) reference_position_0based: Option<usize>,
}

/// One normalized reportable primary-sequence difference.
#[derive(Debug, Clone)]
pub struct Variant {
    pub(crate) contig: String,
    pub(crate) position_1based: usize,
    pub(crate) reference: String,
    pub(crate) alternate: String,
    pub(crate) kind: VariantKind,
    pub(crate) classification: &'static str,
    pub(crate) normalization: &'static str,
    pub(crate) calls: Vec<VariantCallMapping>,
}

/// Variant stage output.
#[derive(Debug, Clone)]
pub struct VariantCallingResult {
    pub(crate) reported: Vec<Variant>,
    pub(crate) excluded_count: usize,
}
