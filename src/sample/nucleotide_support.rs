//! Unweighted accumulation of eligible nucleotide profiles at retained loci.

use crate::error::{Error, Result};
use crate::model::alignment::Orientation;
use crate::model::read_observation::ReadObservation;
use crate::model::sample_evidence::{
    LocusDifferenceObservation, LocusNucleotideSupport, NucleotideContribution,
};

/// Adds each eligible normalized profile with unit read mass.
pub(super) fn aggregate(
    observations: &[LocusDifferenceObservation],
    reads: &[&ReadObservation],
) -> Result<LocusNucleotideSupport> {
    let mut result = LocusNucleotideSupport {
        contributors: 0,
        forward_contributors: 0,
        reverse_contributors: 0,
        support: [0.0; 4],
        forward_support: [0.0; 4],
        reverse_support: [0.0; 4],
    };

    for observation in observations {
        if observation.nucleotide_contribution != NucleotideContribution::Eligible {
            continue;
        }
        let profile = observation
            .signal
            .and_then(|signal| signal.profile)
            .ok_or_else(|| {
                Error::Sample(format!(
                    "eligible nucleotide observation for read {} lacks profile evidence",
                    observation.read_index
                ))
            })?;
        let read = reads.get(observation.read_index).ok_or_else(|| {
            Error::Sample(format!(
                "nucleotide support references missing read {}",
                observation.read_index
            ))
        })?;

        add(&mut result.support, profile.weights);
        result.contributors += 1;
        match read.alignment.orientation {
            Orientation::Forward => {
                add(&mut result.forward_support, profile.weights);
                result.forward_contributors += 1;
            }
            Orientation::Reverse => {
                add(&mut result.reverse_support, profile.weights);
                result.reverse_contributors += 1;
            }
        }
    }

    if result.contributors != result.forward_contributors + result.reverse_contributors
        || !result
            .support
            .iter()
            .chain(result.forward_support.iter())
            .chain(result.reverse_support.iter())
            .all(|value| value.is_finite() && *value >= 0.0)
    {
        return Err(Error::Sample(
            "nucleotide support accumulation is inconsistent".into(),
        ));
    }

    Ok(result)
}

fn add(target: &mut [f64; 4], contribution: [f64; 4]) {
    for (target, contribution) in target.iter_mut().zip(contribution) {
        *target += contribution;
    }
}
