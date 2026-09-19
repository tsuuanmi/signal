//! Sparse extraction of loci where at least one read differs from the reference.

use std::collections::{BTreeMap, BTreeSet};

use crate::error::{Error, Result};
use crate::model::alignment::AlignmentColumn;
use crate::model::read_observation::ReadObservation;
use crate::model::sample_evidence::{
    LocusDifferenceEvidence, LocusDifferenceObservation, LocusState,
};

struct DifferenceBuilder {
    reference_base: char,
    observations: Vec<LocusDifferenceObservation>,
}

pub(super) fn aggregate(reads: &[&ReadObservation]) -> Result<Vec<LocusDifferenceEvidence>> {
    let mut differences: BTreeMap<usize, DifferenceBuilder> = BTreeMap::new();

    for read in reads {
        for column in &read.alignment.columns {
            let Some(reference_index_0based) = column.reference_index_0based else {
                continue;
            };
            if column.reference_base == '-' {
                return Err(Error::Sample(
                    "reference-coordinate difference cannot contain an insertion column".into(),
                ));
            }
            if classify(column) == LocusState::Reference {
                continue;
            }
            let position_1based = reference_index_0based
                .checked_add(1)
                .ok_or_else(|| Error::Sample("reference coordinate overflow".into()))?;
            let entry = differences
                .entry(position_1based)
                .or_insert_with(|| DifferenceBuilder {
                    reference_base: column.reference_base,
                    observations: Vec::new(),
                });
            if entry.reference_base != column.reference_base {
                return Err(Error::Sample(format!(
                    "reference base disagrees at position {position_1based}"
                )));
            }
        }
    }

    if differences.is_empty() {
        return Ok(Vec::new());
    }

    for (read_index, read) in reads.iter().enumerate() {
        let mut seen = BTreeSet::new();
        for column in &read.alignment.columns {
            let Some(reference_index_0based) = column.reference_index_0based else {
                continue;
            };
            let position_1based = reference_index_0based
                .checked_add(1)
                .ok_or_else(|| Error::Sample("reference coordinate overflow".into()))?;
            let Some(entry) = differences.get_mut(&position_1based) else {
                continue;
            };
            if !seen.insert(position_1based) {
                return Err(Error::Sample(format!(
                    "read {} contains duplicate reference coordinate {position_1based}",
                    read.input_sha256
                )));
            }
            if entry.reference_base != column.reference_base {
                return Err(Error::Sample(format!(
                    "reference base disagrees at position {position_1based}"
                )));
            }
            entry
                .observations
                .push(observation(read_index, read, column)?);
        }
    }

    Ok(differences
        .into_iter()
        .map(|(position_1based, built)| LocusDifferenceEvidence {
            position_1based,
            reference_base: built.reference_base,
            observations: built.observations,
        })
        .collect())
}

fn observation(
    read_index: usize,
    read: &ReadObservation,
    column: &AlignmentColumn,
) -> Result<LocusDifferenceObservation> {
    let state = classify(column);
    if state == LocusState::Deletion {
        return Ok(LocusDifferenceObservation {
            read_index,
            state,
            base: None,
            call_index_0based: None,
            relative_quality: None,
        });
    }

    let call_index_0based = column
        .original_call_index_0based
        .ok_or_else(|| Error::Sample("aligned query base lacks original call index".into()))?;
    let quality = read
        .quality
        .per_call
        .get(call_index_0based)
        .filter(|quality| quality.index_0based == call_index_0based)
        .ok_or_else(|| Error::Sample("aligned call lacks matching quality evidence".into()))?;

    Ok(LocusDifferenceObservation {
        read_index,
        state,
        base: Some(column.query_base),
        call_index_0based: Some(call_index_0based),
        relative_quality: Some(quality.relative_quality_score),
    })
}

fn classify(column: &AlignmentColumn) -> LocusState {
    if column.query_base == '-' {
        LocusState::Deletion
    } else if !is_canonical(column.query_base) || !is_canonical(column.reference_base) {
        LocusState::Unresolved
    } else if column.query_base == column.reference_base {
        LocusState::Reference
    } else {
        LocusState::Alternate
    }
}

const fn is_canonical(base: char) -> bool {
    matches!(base, 'A' | 'C' | 'G' | 'T')
}
