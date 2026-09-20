//! Continuous candidate phase evidence from one independently placed read.

use std::collections::BTreeMap;

use crate::error::{Error, Result};
use crate::model::alignment::Alignment;
use crate::model::locus_evidence::EvidenceProfile;
use crate::model::phase::{
    PhaseApplicability, PhaseCandidateEvidence, PhaseEvidenceAvailability, PhaseInsufficiency,
    PhaseTractEvidence, PhaseWindowEvidence, ReadPhaseEvidence,
};
use crate::model::reference::Reference;
use crate::model::signal::SignalAnalysis;

use super::geometry::{self, TRACTS, Tract};

#[derive(Debug, Clone, Copy)]
struct MappedObservation {
    reference_index_0based: usize,
    reference_base: char,
    query_base: char,
    call_index_0based: Option<usize>,
    profile: Option<EvidenceProfile>,
}

#[derive(Debug, Clone, Copy)]
struct AfterObservation {
    distance: usize,
    reference_base: char,
    call_index_0based: usize,
    profile: Option<EvidenceProfile>,
}

#[derive(Debug, Clone, Copy)]
struct CandidateContribution {
    zero_mass: f64,
    shifted_mass: f64,
    residual_mass: f64,
}

/// Computes signal.polyc_phase/v1 continuous read-local evidence.
///
/// The method is measurement-only: it selects no winning offset and produces no phase
/// state, confidence value, contribution weight, variant mutation, or no-call decision.
pub(crate) fn measure(
    alignment: &Alignment,
    signal: &SignalAnalysis,
    reference: &Reference,
) -> Result<ReadPhaseEvidence> {
    if !geometry::supported_reference(reference)? {
        return Ok(ReadPhaseEvidence {
            applicability: PhaseApplicability::NotApplicable,
            tracts: Vec::new(),
        });
    }

    let mapped = mapped_observations(alignment, signal, reference)?;
    let mut by_reference = BTreeMap::new();
    for observation in &mapped {
        if by_reference
            .insert(observation.reference_index_0based, *observation)
            .is_some()
        {
            return Err(Error::Phase(format!(
                "selected read contains duplicate reference coordinate {}",
                observation.reference_index_0based + 1
            )));
        }
    }

    let tracts = TRACTS
        .into_iter()
        .map(|tract| tract_evidence(tract, alignment, &by_reference))
        .collect::<Result<Vec<_>>>()?;

    Ok(ReadPhaseEvidence {
        applicability: PhaseApplicability::Applicable,
        tracts,
    })
}

fn mapped_observations(
    alignment: &Alignment,
    signal: &SignalAnalysis,
    reference: &Reference,
) -> Result<Vec<MappedObservation>> {
    let reference_bytes = reference.sequence.as_bytes();
    alignment
        .columns
        .iter()
        .filter_map(|column| {
            column.reference_index_0based.map(|reference_index_0based| {
                let reference_base = reference_bytes
                    .get(reference_index_0based)
                    .copied()
                    .map(char::from)
                    .ok_or_else(|| {
                        Error::Phase(format!(
                            "alignment references out-of-range coordinate {}",
                            reference_index_0based + 1
                        ))
                    })?;
                if column.reference_base != reference_base {
                    return Err(Error::Phase(format!(
                        "alignment/reference base mismatch at position {}",
                        reference_index_0based + 1
                    )));
                }

                let profile = match column.original_call_index_0based {
                    Some(call_index_0based) => {
                        let locus = signal.loci.get(call_index_0based).ok_or_else(|| {
                            Error::Phase(format!(
                                "alignment references missing signal locus {call_index_0based}"
                            ))
                        })?;
                        if locus.call_index_0based != call_index_0based {
                            return Err(Error::Phase(format!(
                                "signal locus index {} does not match requested call {call_index_0based}",
                                locus.call_index_0based
                            )));
                        }
                        locus
                            .profile
                            .map(|profile| match alignment.orientation {
                                crate::model::alignment::Orientation::Forward => profile,
                                crate::model::alignment::Orientation::Reverse => {
                                    profile.complemented()
                                }
                            })
                            .map(validate_profile)
                            .transpose()?
                    }
                    None => None,
                };

                Ok(MappedObservation {
                    reference_index_0based,
                    reference_base,
                    query_base: column.query_base,
                    call_index_0based: column.original_call_index_0based,
                    profile,
                })
            })
        })
        .collect()
}

fn tract_evidence(
    tract: Tract,
    alignment: &Alignment,
    by_reference: &BTreeMap<usize, MappedObservation>,
) -> Result<PhaseTractEvidence> {
    let covered = (tract.start_0based..=tract.end_0based_inclusive)
        .filter_map(|position| by_reference.get(&position).copied())
        .collect::<Vec<_>>();
    let expected_coverage = tract.end_0based_inclusive - tract.start_0based + 1;

    if covered.is_empty() {
        return Ok(insufficient(
            tract,
            PhaseInsufficiency::NoTractCoverage,
            None,
        ));
    }
    if covered.len() != expected_coverage {
        return Ok(insufficient(
            tract,
            PhaseInsufficiency::IncompleteTractCoverage,
            interrupt_base(tract, by_reference),
        ));
    }

    let call_indices = covered
        .iter()
        .filter_map(|observation| observation.call_index_0based)
        .collect::<Vec<_>>();
    let Some(last_tract_call) = call_indices.iter().copied().max() else {
        return Ok(insufficient(
            tract,
            PhaseInsufficiency::NoCallBackedTractSpan,
            interrupt_base(tract, by_reference),
        ));
    };

    let mut after = by_reference
        .values()
        .filter_map(|observation| {
            let call_index_0based = observation.call_index_0based?;
            if call_index_0based <= last_tract_call
                || geometry::contains(tract, observation.reference_index_0based)
            {
                return None;
            }
            let distance = geometry::distance_after(
                tract,
                alignment.orientation,
                observation.reference_index_0based,
            );
            (distance > 0).then_some(AfterObservation {
                distance,
                reference_base: observation.reference_base,
                call_index_0based,
                profile: observation.profile,
            })
        })
        .collect::<Vec<_>>();
    after.sort_by_key(|observation| observation.distance);
    for pair in after.windows(2) {
        if pair[0].distance == pair[1].distance {
            return Err(Error::Phase(format!(
                "{} has duplicate post-tract reference distance {}",
                tract.id.label(),
                pair[0].distance
            )));
        }
    }

    let profiled = after
        .iter()
        .copied()
        .filter(|observation| {
            observation.profile.is_some() && canonical_index(observation.reference_base).is_some()
        })
        .collect::<Vec<_>>();
    if profiled.len() < super::WINDOW_PROFILE_OBSERVATIONS {
        return Ok(insufficient(
            tract,
            PhaseInsufficiency::NoCompleteProfileWindow,
            interrupt_base(tract, by_reference),
        ));
    }

    let reference_by_distance = after
        .iter()
        .map(|observation| (observation.distance, observation.reference_base))
        .collect::<BTreeMap<_, _>>();
    let mut windows = Vec::new();
    for start in (0..=profiled.len() - super::WINDOW_PROFILE_OBSERVATIONS)
        .step_by(super::WINDOW_STEP_PROFILE_OBSERVATIONS)
    {
        let window = &profiled[start..start + super::WINDOW_PROFILE_OBSERVATIONS];
        windows.push(window_evidence(window, &reference_by_distance)?);
    }

    if windows.is_empty() {
        return Ok(insufficient(
            tract,
            PhaseInsufficiency::NoCompleteProfileWindow,
            interrupt_base(tract, by_reference),
        ));
    }

    Ok(PhaseTractEvidence {
        tract: tract.id,
        availability: PhaseEvidenceAvailability::Measured,
        interrupt_aligned_base: interrupt_base(tract, by_reference),
        windows,
    })
}

fn insufficient(
    tract: Tract,
    reason: PhaseInsufficiency,
    interrupt_aligned_base: Option<char>,
) -> PhaseTractEvidence {
    PhaseTractEvidence {
        tract: tract.id,
        availability: PhaseEvidenceAvailability::Insufficient(reason),
        interrupt_aligned_base,
        windows: Vec::new(),
    }
}

fn interrupt_base(
    tract: Tract,
    by_reference: &BTreeMap<usize, MappedObservation>,
) -> Option<char> {
    by_reference
        .get(&tract.interrupt_0based)
        .filter(|observation| observation.call_index_0based.is_some())
        .map(|observation| observation.query_base)
        .filter(|base| canonical_index(*base).is_some())
}

fn window_evidence(
    window: &[AfterObservation],
    reference_by_distance: &BTreeMap<usize, char>,
) -> Result<PhaseWindowEvidence> {
    let first = window
        .first()
        .ok_or_else(|| Error::Phase("phase window is empty".into()))?;
    let last = window
        .last()
        .ok_or_else(|| Error::Phase("phase window is empty".into()))?;

    let mut impurities = Vec::with_capacity(window.len());
    let mut zero_masses = Vec::with_capacity(window.len());
    for observation in window {
        let profile = observation
            .profile
            .ok_or_else(|| Error::Phase("phase window contains missing profile".into()))?;
        let zero_mass = mass(profile, observation.reference_base).ok_or_else(|| {
            Error::Phase("phase window contains non-canonical reference base".into())
        })?;
        zero_masses.push(zero_mass);
        impurities.push(1.0 - profile.weights.iter().copied().fold(0.0_f64, f64::max));
    }

    let candidates = super::CANDIDATE_OFFSETS
        .into_iter()
        .map(|offset| candidate_evidence(window, reference_by_distance, offset))
        .collect::<Result<Vec<_>>>()?;

    Ok(PhaseWindowEvidence {
        start_distance_after_tract: first.distance,
        end_distance_after_tract: last.distance,
        start_call_index_0based: first.call_index_0based,
        end_call_index_0based: last.call_index_0based,
        profile_observations: window.len(),
        mean_profile_impurity: mean(&impurities),
        mean_zero_reference_mass: mean(&zero_masses),
        candidates,
    })
}

fn candidate_evidence(
    window: &[AfterObservation],
    reference_by_distance: &BTreeMap<usize, char>,
    offset: i8,
) -> Result<PhaseCandidateEvidence> {
    let mut contributions = Vec::new();
    for observation in window {
        let Some(shifted_distance) = observation
            .distance
            .checked_add_signed(isize::from(offset))
            .filter(|distance| *distance > 0)
        else {
            continue;
        };
        let Some(&shifted_base) = reference_by_distance.get(&shifted_distance) else {
            continue;
        };
        if shifted_base == observation.reference_base
            || canonical_index(shifted_base).is_none()
            || canonical_index(observation.reference_base).is_none()
        {
            continue;
        }
        let profile = observation
            .profile
            .ok_or_else(|| Error::Phase("candidate window contains missing profile".into()))?;
        let zero_mass = mass(profile, observation.reference_base)
            .ok_or_else(|| Error::Phase("candidate zero base is non-canonical".into()))?;
        let shifted_mass = mass(profile, shifted_base)
            .ok_or_else(|| Error::Phase("candidate shifted base is non-canonical".into()))?;
        let residual = 1.0 - zero_mass - shifted_mass;
        if residual < -1e-9 {
            return Err(Error::Phase(
                "candidate phase mass exceeds normalized profile mass".into(),
            ));
        }
        contributions.push(CandidateContribution {
            zero_mass,
            shifted_mass,
            residual_mass: residual.max(0.0),
        });
    }

    if contributions.is_empty() {
        return Ok(PhaseCandidateEvidence {
            reference_offset_in_read_order: offset,
            informative_positions: 0,
            mean_zero_reference_mass: None,
            mean_shifted_reference_mass: None,
            mean_residual_mass: None,
        });
    }

    Ok(PhaseCandidateEvidence {
        reference_offset_in_read_order: offset,
        informative_positions: contributions.len(),
        mean_zero_reference_mass: Some(mean(
            &contributions
                .iter()
                .map(|contribution| contribution.zero_mass)
                .collect::<Vec<_>>(),
        )),
        mean_shifted_reference_mass: Some(mean(
            &contributions
                .iter()
                .map(|contribution| contribution.shifted_mass)
                .collect::<Vec<_>>(),
        )),
        mean_residual_mass: Some(mean(
            &contributions
                .iter()
                .map(|contribution| contribution.residual_mass)
                .collect::<Vec<_>>(),
        )),
    })
}

fn validate_profile(profile: EvidenceProfile) -> Result<EvidenceProfile> {
    let total = profile.weights.iter().sum::<f64>();
    if profile
        .weights
        .iter()
        .any(|value| !value.is_finite() || !(0.0..=1.0).contains(value))
        || (total - 1.0).abs() > 1e-9
    {
        return Err(Error::Phase(
            "evidence profile must contain finite normalized A/C/G/T mass".into(),
        ));
    }
    Ok(profile)
}

fn mass(profile: EvidenceProfile, base: char) -> Option<f64> {
    canonical_index(base).map(|index| profile.weights[index])
}

const fn canonical_index(base: char) -> Option<usize> {
    match base {
        'A' => Some(0),
        'C' => Some(1),
        'G' => Some(2),
        'T' => Some(3),
        _ => None,
    }
}

fn mean(values: &[f64]) -> f64 {
    values.iter().sum::<f64>() / values.len() as f64
}
