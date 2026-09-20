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
        let evidence = ReadPhaseEvidence {
            applicability: PhaseApplicability::NotApplicable,
            tracts: Vec::new(),
        };
        validate_evidence(&evidence)?;
        return Ok(evidence);
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

    let evidence = ReadPhaseEvidence {
        applicability: PhaseApplicability::Applicable,
        tracts,
    };
    validate_evidence(&evidence)?;
    Ok(evidence)
}

fn validate_evidence(evidence: &ReadPhaseEvidence) -> Result<()> {
    match evidence.applicability {
        PhaseApplicability::NotApplicable => {
            if !evidence.tracts.is_empty() {
                return Err(Error::Phase(
                    "non-applicable phase evidence must not contain tract records".into(),
                ));
            }
            return Ok(());
        }
        PhaseApplicability::Applicable => {
            if evidence.tracts.len() != TRACTS.len() {
                return Err(Error::Phase(format!(
                    "applicable phase evidence must contain {} tract records",
                    TRACTS.len()
                )));
            }
        }
    }

    for (index, tract) in evidence.tracts.iter().enumerate() {
        if tract.tract != TRACTS[index].id {
            return Err(Error::Phase(
                "phase tract records are not in canonical method order".into(),
            ));
        }
        if tract
            .interrupt_aligned_base
            .is_some_and(|base| canonical_index(base).is_none())
        {
            return Err(Error::Phase(
                "phase interrupt evidence must be canonical A/C/G/T".into(),
            ));
        }

        match tract.availability {
            PhaseEvidenceAvailability::Insufficient(reason) => {
                match reason {
                    PhaseInsufficiency::NoTractCoverage
                    | PhaseInsufficiency::IncompleteTractCoverage
                    | PhaseInsufficiency::NoCallBackedTractSpan
                    | PhaseInsufficiency::NoCompleteProfileWindow => {}
                }
                if !tract.windows.is_empty() {
                    return Err(Error::Phase(
                        "insufficient phase evidence must not contain windows".into(),
                    ));
                }
            }
            PhaseEvidenceAvailability::Measured => {
                if tract.windows.is_empty() {
                    return Err(Error::Phase(
                        "measured phase evidence must contain at least one window".into(),
                    ));
                }
            }
        }

        for window in &tract.windows {
            if window.profile_observations != super::WINDOW_PROFILE_OBSERVATIONS
                || window.start_distance_after_tract == 0
                || window.start_distance_after_tract > window.end_distance_after_tract
                || window.start_call_index_0based > window.end_call_index_0based
                || !unit_interval(window.mean_profile_impurity)
                || !unit_interval(window.mean_zero_reference_mass)
                || window.candidates.len() != super::CANDIDATE_OFFSETS.len()
            {
                return Err(Error::Phase(
                    "phase window evidence violates the v1 method contract".into(),
                ));
            }

            for (candidate_index, candidate) in window.candidates.iter().enumerate() {
                if candidate.reference_offset_in_read_order
                    != super::CANDIDATE_OFFSETS[candidate_index]
                {
                    return Err(Error::Phase(
                        "phase candidates are not in canonical offset order".into(),
                    ));
                }
                if candidate.informative_positions > window.profile_observations {
                    return Err(Error::Phase(
                        "phase candidate informative count exceeds window size".into(),
                    ));
                }

                let masses = [
                    candidate.mean_zero_reference_mass,
                    candidate.mean_shifted_reference_mass,
                    candidate.mean_residual_mass,
                ];
                if candidate.informative_positions == 0 {
                    if masses.iter().any(Option::is_some) {
                        return Err(Error::Phase(
                            "non-informative phase candidate must not contain mean masses".into(),
                        ));
                    }
                    continue;
                }
                let [Some(zero), Some(shifted), Some(residual)] = masses else {
                    return Err(Error::Phase(
                        "informative phase candidate must contain all mean masses".into(),
                    ));
                };
                if !unit_interval(zero)
                    || !unit_interval(shifted)
                    || !unit_interval(residual)
                    || (zero + shifted + residual - 1.0).abs() > 1e-9
                {
                    return Err(Error::Phase(
                        "phase candidate mean masses must be finite and sum to one".into(),
                    ));
                }
            }
        }
    }
    Ok(())
}

fn unit_interval(value: f64) -> bool {
    value.is_finite() && (0.0..=1.0).contains(&value)
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

    let Some(last_tract_call) = covered
        .iter()
        .filter_map(|observation| observation.call_index_0based)
        .max()
    else {
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

fn interrupt_base(tract: Tract, by_reference: &BTreeMap<usize, MappedObservation>) -> Option<char> {
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

    let count = contributions.len() as f64;
    Ok(PhaseCandidateEvidence {
        reference_offset_in_read_order: offset,
        informative_positions: contributions.len(),
        mean_zero_reference_mass: Some(
            contributions
                .iter()
                .map(|contribution| contribution.zero_mass)
                .sum::<f64>()
                / count,
        ),
        mean_shifted_reference_mass: Some(
            contributions
                .iter()
                .map(|contribution| contribution.shifted_mass)
                .sum::<f64>()
                / count,
        ),
        mean_residual_mass: Some(
            contributions
                .iter()
                .map(|contribution| contribution.residual_mass)
                .sum::<f64>()
                / count,
        ),
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

#[cfg(test)]
mod tests {
    use crate::model::alignment::{
        AlignmentColumn, AlignmentMetrics, Orientation, ReferenceSegment,
    };
    use crate::model::locus_evidence::LocusEvidence;
    use crate::model::phase::{PhaseEvidenceAvailability, PhaseInsufficiency, PhaseTractId};
    use crate::model::reference::ReferenceTopology;
    use crate::model::signal::{SignalAnalysis, TraceIntegrity};

    use super::*;
    use crate::phase::geometry::{RCRS_LENGTH, RCRS_SEQUENCE_SHA256, TRACTS};

    fn canonical_reference() -> Reference {
        let mut sequence = vec![b'A'; RCRS_LENGTH];
        for tract in TRACTS {
            sequence[tract.start_0based..=tract.end_0based_inclusive]
                .copy_from_slice(tract.reference_sequence.as_bytes());
        }
        for (index, position) in (315..350).enumerate() {
            sequence[position] = b"ACGT"[index % 4];
        }
        Reference {
            name: "rCRS".into(),
            sequence: String::from_utf8(sequence).expect("synthetic rCRS is ASCII"),
            topology: ReferenceTopology::Circular,
            sequence_sha256: RCRS_SEQUENCE_SHA256.into(),
        }
    }

    fn one_hot(base: char) -> EvidenceProfile {
        let mut weights = [0.0; 4];
        weights[canonical_index(base).expect("canonical test base")] = 1.0;
        EvidenceProfile { weights }
    }

    fn mixture(zero: char, shifted: char) -> EvidenceProfile {
        let mut weights = [0.0; 4];
        weights[canonical_index(zero).expect("canonical zero base")] = 0.60;
        weights[canonical_index(shifted).expect("canonical shifted base")] = 0.35;
        let residual = ['A', 'C', 'G', 'T']
            .into_iter()
            .find(|base| *base != zero && *base != shifted)
            .expect("residual base");
        weights[canonical_index(residual).expect("canonical residual base")] = 0.05;
        EvidenceProfile { weights }
    }

    fn locus(index: usize, profile: Option<EvidenceProfile>) -> LocusEvidence {
        LocusEvidence {
            call_index_0based: index,
            ploc_0based: index,
            window_start_0based: index,
            window_end_0based_exclusive: index + 1,
            context_call_start_0based: index,
            context_call_end_0based_exclusive: index + 1,
            context_sample_start_0based: index,
            context_sample_end_0based_exclusive: index + 1,
            event_position_0based: index,
            channel_heights: [0; 4],
            channel_baselines: [0.0; 4],
            channel_noise_sigmas: [1.0; 4],
            corrected_amplitudes: profile.map_or([0.0; 4], |value| value.weights),
            snrs: [0.0; 4],
            profile,
        }
    }

    fn signal(profiles: Vec<Option<EvidenceProfile>>) -> SignalAnalysis {
        SignalAnalysis {
            integrity: TraceIntegrity {
                ploc_count: profiles.len(),
                vendor_primary_count: None,
                vendor_quality_count: None,
                minimum_ploc_spacing: None,
                median_ploc_spacing: None,
                maximum_ploc_spacing: None,
                clipped_channel_samples: 0,
                maximum_to_median_event_signal_ratio: None,
            },
            loci: profiles
                .into_iter()
                .enumerate()
                .map(|(index, profile)| locus(index, profile))
                .collect(),
            windows: Vec::new(),
            noisy_regions: Vec::new(),
        }
    }

    fn alignment(orientation: Orientation, columns: Vec<AlignmentColumn>) -> Alignment {
        Alignment {
            orientation,
            score: 0,
            reference_segments: vec![ReferenceSegment {
                start_0based: 0,
                end_0based_exclusive: RCRS_LENGTH,
            }],
            wraps_origin: false,
            metrics: AlignmentMetrics {
                exact_matches: columns.len(),
                mismatches: 0,
                gap_opens: 0,
                callable_columns: columns.len(),
                callable_identity: 1.0,
                unresolved_query_bases: 0,
            },
            columns,
        }
    }

    fn forward_hv2_read(
        reference: &Reference,
        after_count: usize,
        missing_profile_distance: Option<usize>,
    ) -> (Alignment, SignalAnalysis) {
        let tract = TRACTS[0];
        let mut columns = Vec::new();
        let mut profiles = Vec::new();
        let mut call = 0usize;

        for position in tract.start_0based..=tract.end_0based_inclusive {
            let base = char::from(reference.sequence.as_bytes()[position]);
            columns.push(AlignmentColumn {
                query_base: base,
                reference_base: base,
                original_call_index_0based: Some(call),
                reference_index_0based: Some(position),
            });
            profiles.push(Some(one_hot(base)));
            call += 1;
        }

        for distance in 1..=after_count {
            let position = (tract.end_0based_inclusive + distance) % RCRS_LENGTH;
            let base = char::from(reference.sequence.as_bytes()[position]);
            let shifted_position = (position + 1) % RCRS_LENGTH;
            let shifted = char::from(reference.sequence.as_bytes()[shifted_position]);
            columns.push(AlignmentColumn {
                query_base: base,
                reference_base: base,
                original_call_index_0based: Some(call),
                reference_index_0based: Some(position),
            });
            let profile =
                (missing_profile_distance != Some(distance)).then(|| mixture(base, shifted));
            profiles.push(profile);
            call += 1;
        }

        (alignment(Orientation::Forward, columns), signal(profiles))
    }

    #[test]
    fn unsupported_reference_is_not_applicable() -> Result<()> {
        let mut reference = canonical_reference();
        reference.sequence_sha256 = "0".repeat(64);
        let evidence = measure(
            &alignment(Orientation::Forward, Vec::new()),
            &signal(Vec::new()),
            &reference,
        )?;

        assert_eq!(evidence.applicability, PhaseApplicability::NotApplicable);
        assert!(evidence.tracts.is_empty());
        Ok(())
    }

    #[test]
    fn complete_hv2_read_preserves_candidate_curve() -> Result<()> {
        let reference = canonical_reference();
        let (alignment, signal) = forward_hv2_read(&reference, 30, None);
        let evidence = measure(&alignment, &signal, &reference)?;

        assert_eq!(evidence.applicability, PhaseApplicability::Applicable);
        let hv2 = evidence
            .tracts
            .iter()
            .find(|tract| tract.tract == PhaseTractId::Hv2)
            .expect("HV2 evidence");
        assert_eq!(hv2.availability, PhaseEvidenceAvailability::Measured);
        assert_eq!(hv2.windows.len(), 2);
        assert_eq!(hv2.windows[0].start_distance_after_tract, 1);
        assert_eq!(hv2.windows[0].end_distance_after_tract, 25);
        assert_eq!(hv2.windows[0].profile_observations, 25);
        assert!((hv2.windows[0].mean_zero_reference_mass - 0.60).abs() < 1e-12);

        let plus_one = hv2.windows[0]
            .candidates
            .iter()
            .find(|candidate| candidate.reference_offset_in_read_order == 1)
            .expect("+1 candidate");
        assert_eq!(plus_one.informative_positions, 25);
        assert!((plus_one.mean_shifted_reference_mass.expect("shifted mass") - 0.35).abs() < 1e-12);
        assert!((plus_one.mean_residual_mass.expect("residual mass") - 0.05).abs() < 1e-12);
        Ok(())
    }

    #[test]
    fn profile_gap_is_skipped_without_interval_membership_fallback() -> Result<()> {
        let reference = canonical_reference();
        let (alignment, signal) = forward_hv2_read(&reference, 26, Some(3));
        let evidence = measure(&alignment, &signal, &reference)?;
        let hv2 = evidence
            .tracts
            .iter()
            .find(|tract| tract.tract == PhaseTractId::Hv2)
            .expect("HV2 evidence");

        assert_eq!(hv2.availability, PhaseEvidenceAvailability::Measured);
        assert_eq!(hv2.windows.len(), 1);
        assert_eq!(hv2.windows[0].start_distance_after_tract, 1);
        assert_eq!(hv2.windows[0].end_distance_after_tract, 26);
        assert_eq!(hv2.windows[0].profile_observations, 25);
        Ok(())
    }

    #[test]
    fn partial_tract_coverage_is_explicitly_insufficient() -> Result<()> {
        let reference = canonical_reference();
        let (mut alignment, signal) = forward_hv2_read(&reference, 30, None);
        alignment
            .columns
            .retain(|column| column.reference_index_0based != Some(305));
        let evidence = measure(&alignment, &signal, &reference)?;
        let hv2 = evidence
            .tracts
            .iter()
            .find(|tract| tract.tract == PhaseTractId::Hv2)
            .expect("HV2 evidence");

        assert_eq!(
            hv2.availability,
            PhaseEvidenceAvailability::Insufficient(PhaseInsufficiency::IncompleteTractCoverage)
        );
        assert!(hv2.windows.is_empty());
        Ok(())
    }

    #[test]
    fn same_reference_base_is_noninformative_for_candidate() -> Result<()> {
        let observation = AfterObservation {
            distance: 1,
            reference_base: 'A',
            call_index_0based: 1,
            profile: Some(EvidenceProfile {
                weights: [0.7, 0.1, 0.1, 0.1],
            }),
        };
        let reference_by_distance = BTreeMap::from([(1, 'A'), (2, 'A')]);
        let candidate = candidate_evidence(&[observation], &reference_by_distance, 1)?;

        assert_eq!(candidate.informative_positions, 0);
        assert!(candidate.mean_zero_reference_mass.is_none());
        assert!(candidate.mean_shifted_reference_mass.is_none());
        assert!(candidate.mean_residual_mass.is_none());
        Ok(())
    }

    #[test]
    fn incomplete_window_is_explicitly_insufficient() -> Result<()> {
        let reference = canonical_reference();
        let (alignment, signal) = forward_hv2_read(&reference, 24, None);
        let evidence = measure(&alignment, &signal, &reference)?;
        let hv2 = evidence
            .tracts
            .iter()
            .find(|tract| tract.tract == PhaseTractId::Hv2)
            .expect("HV2 evidence");

        assert_eq!(
            hv2.availability,
            PhaseEvidenceAvailability::Insufficient(PhaseInsufficiency::NoCompleteProfileWindow)
        );
        assert!(hv2.windows.is_empty());
        Ok(())
    }

    #[test]
    fn reverse_alignment_profiles_are_projected_to_reference_channels() -> Result<()> {
        let reference = Reference {
            name: "test".into(),
            sequence: "A".into(),
            topology: ReferenceTopology::Linear,
            sequence_sha256: String::new(),
        };
        let alignment = Alignment {
            orientation: Orientation::Reverse,
            score: 0,
            reference_segments: vec![ReferenceSegment {
                start_0based: 0,
                end_0based_exclusive: 1,
            }],
            wraps_origin: false,
            metrics: AlignmentMetrics {
                exact_matches: 1,
                mismatches: 0,
                gap_opens: 0,
                callable_columns: 1,
                callable_identity: 1.0,
                unresolved_query_bases: 0,
            },
            columns: vec![AlignmentColumn {
                query_base: 'A',
                reference_base: 'A',
                original_call_index_0based: Some(0),
                reference_index_0based: Some(0),
            }],
        };
        let signal = signal(vec![Some(EvidenceProfile {
            weights: [0.0, 0.0, 0.0, 1.0],
        })]);

        let mapped = mapped_observations(&alignment, &signal, &reference)?;
        assert_eq!(
            mapped[0].profile.map(|profile| profile.weights),
            Some([1.0, 0.0, 0.0, 0.0])
        );
        Ok(())
    }
}
