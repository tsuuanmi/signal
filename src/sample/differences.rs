//! Sparse extraction of non-reference locus evidence.

use std::collections::BTreeMap;

use crate::error::{Error, Result};
use crate::model::alignment::AlignmentColumn;
use crate::model::read_observation::ReadObservation;
use crate::model::sample_evidence::{
    LocusDifferenceEvidence, LocusDifferenceObservation, LocusDifferenceState,
};

struct DifferenceBuilder {
    reference_base: char,
    observations: Vec<LocusDifferenceObservation>,
}

pub(super) fn aggregate(reads: &[&ReadObservation]) -> Result<Vec<LocusDifferenceEvidence>> {
    let mut differences: BTreeMap<usize, DifferenceBuilder> = BTreeMap::new();

    for (read_index, read) in reads.iter().enumerate() {
        for column in &read.alignment.columns {
            let Some(reference_index_0based) = column.reference_index_0based else {
                continue;
            };
            let Some(observation) = observation(read_index, read, column)? else {
                continue;
            };
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
            entry.observations.push(observation);
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
) -> Result<Option<LocusDifferenceObservation>> {
    if column.reference_base == '-' {
        return Err(Error::Sample(
            "reference-coordinate difference cannot contain an insertion column".into(),
        ));
    }
    if column.query_base == '-' {
        return Ok(Some(LocusDifferenceObservation {
            read_index,
            state: LocusDifferenceState::Deletion,
            base: None,
            call_index_0based: None,
            relative_quality: None,
        }));
    }

    let state = if !is_canonical(column.query_base) || !is_canonical(column.reference_base) {
        LocusDifferenceState::Unresolved
    } else if column.query_base == column.reference_base {
        return Ok(None);
    } else {
        LocusDifferenceState::Alternate
    };

    let call_index_0based = column
        .original_call_index_0based
        .ok_or_else(|| Error::Sample("aligned query base lacks original call index".into()))?;
    let quality = read
        .quality
        .per_call
        .get(call_index_0based)
        .filter(|quality| quality.index_0based == call_index_0based)
        .ok_or_else(|| Error::Sample("aligned call lacks matching quality evidence".into()))?;

    Ok(Some(LocusDifferenceObservation {
        read_index,
        state,
        base: Some(column.query_base),
        call_index_0based: Some(call_index_0based),
        relative_quality: Some(quality.relative_quality_score),
    }))
}

const fn is_canonical(base: char) -> bool {
    matches!(base, 'A' | 'C' | 'G' | 'T')
}
