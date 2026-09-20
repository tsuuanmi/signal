//! Read-local post-poly-C phase evidence after selected reference placement.

/// Whether the current reference/context can support the promoted phase method.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum PhaseApplicability {
    NotApplicable,
    Applicable,
}

/// Supported canonical rCRS poly-C tract.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum PhaseTractId {
    Hv2,
    Hv1,
}

impl PhaseTractId {
    pub(crate) const fn label(self) -> &'static str {
        match self {
            Self::Hv2 => "HV2_C",
            Self::Hv1 => "HV1_C",
        }
    }
}

/// Structural reason an applicable tract cannot produce a complete measurement window.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum PhaseInsufficiency {
    NoTractCoverage,
    IncompleteTractCoverage,
    NoCallBackedTractSpan,
    NoCompleteProfileWindow,
}

/// Evidence availability for one supported tract.
///
/// This is not a phase-state or reliability classification.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum PhaseEvidenceAvailability {
    Insufficient(PhaseInsufficiency),
    Measured,
}

/// Complete continuous candidate evidence for one window and one non-zero offset.
#[derive(Debug, Clone, PartialEq)]
pub(crate) struct PhaseCandidateEvidence {
    pub(crate) reference_offset_in_read_order: i8,
    pub(crate) informative_positions: usize,
    pub(crate) mean_zero_reference_mass: Option<f64>,
    pub(crate) mean_shifted_reference_mass: Option<f64>,
    pub(crate) mean_residual_mass: Option<f64>,
}

/// One exact window of consecutive profile-bearing post-tract observations.
#[derive(Debug, Clone, PartialEq)]
pub(crate) struct PhaseWindowEvidence {
    pub(crate) start_distance_after_tract: usize,
    pub(crate) end_distance_after_tract: usize,
    pub(crate) start_call_index_0based: usize,
    pub(crate) end_call_index_0based: usize,
    pub(crate) profile_observations: usize,
    pub(crate) mean_profile_impurity: f64,
    pub(crate) mean_zero_reference_mass: f64,
    pub(crate) candidates: Vec<PhaseCandidateEvidence>,
}

/// Read-local evidence for one supported rCRS tract.
#[derive(Debug, Clone, PartialEq)]
pub(crate) struct PhaseTractEvidence {
    pub(crate) tract: PhaseTractId,
    pub(crate) availability: PhaseEvidenceAvailability,
    pub(crate) interrupt_aligned_base: Option<char>,
    pub(crate) windows: Vec<PhaseWindowEvidence>,
}

/// Complete read-local phase evidence.
///
/// A non-applicable reference has no tract records. An applicable reference retains one
/// record per supported tract, including explicit insufficient-evidence reasons.
#[derive(Debug, Clone, PartialEq)]
pub(crate) struct ReadPhaseEvidence {
    pub(crate) applicability: PhaseApplicability,
    pub(crate) tracts: Vec<PhaseTractEvidence>,
}
