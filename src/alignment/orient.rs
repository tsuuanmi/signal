//! Forward/reverse profile alignment selection and circular coordinate projection.

use std::cmp::Ordering;

use crate::alignment::gotoh;
use crate::alignment::traceback::RawAlignment;
use crate::config::AlignmentConfig;
use crate::error::{Error, Result};
use crate::model::alignment::{Alignment, AlignmentColumn, Orientation, ReferenceSegment};
use crate::model::locus_evidence::EvidenceProfile;
use crate::model::nucleotide::reverse_complement;
use crate::model::quality::QualityControlResult;
use crate::model::reference::{Reference, ReferenceTopology};
use crate::model::signal::SignalAnalysis;

struct Candidate {
    orientation: Orientation,
    mapping: Vec<usize>,
    placements: Vec<RawAlignment>,
}

/// Aligns both evidence-profile orientations and returns one unique selected result.
pub(crate) fn align_best(
    qc: &QualityControlResult,
    signal: &SignalAnalysis,
    reference: &Reference,
    config: &AlignmentConfig,
) -> Result<Alignment> {
    let forward_query = qc.retained_sequence.clone();
    let reverse_query = reverse_complement(&forward_query);
    let forward_profiles = retained_profiles(qc, signal)?;
    let reverse_profiles = forward_profiles
        .iter()
        .rev()
        .map(|profile| profile.map(EvidenceProfile::complemented))
        .collect::<Vec<_>>();
    let forward_mapping = (qc.trim_start_0based..qc.trim_end_0based_exclusive).collect();
    let reverse_mapping = (qc.trim_start_0based..qc.trim_end_0based_exclusive)
        .rev()
        .collect();
    let (working_reference, modulo_length) = match reference.topology {
        ReferenceTopology::Linear => (reference.sequence.clone(), None),
        ReferenceTopology::Circular => (
            format!("{}{}", reference.sequence, reference.sequence),
            Some(reference.len()),
        ),
    };
    let forward = Candidate {
        orientation: Orientation::Forward,
        mapping: forward_mapping,
        placements: gotoh::align(
            &forward_query,
            &forward_profiles,
            &working_reference,
            config,
            modulo_length,
        )?,
    };
    let reverse = Candidate {
        orientation: Orientation::Reverse,
        mapping: reverse_mapping,
        placements: gotoh::align(
            &reverse_query,
            &reverse_profiles,
            &working_reference,
            config,
            modulo_length,
        )?,
    };
    let ordering = compare(&forward.placements[0], &reverse.placements[0]);
    let selected = match ordering {
        Ordering::Greater => &forward,
        Ordering::Less => &reverse,
        Ordering::Equal => {
            return Err(Error::Alignment(
                "forward and reverse evidence-profile scores are tied".into(),
            ));
        }
    };
    if selected.placements.len() != 1 {
        return Err(Error::Alignment(
            "selected orientation has multiple equally scoring placements".into(),
        ));
    }
    let raw = &selected.placements[0];
    if raw.metrics.callable_columns < config.minimum_callable_bases {
        return Err(Error::Alignment(format!(
            "alignment has {} callable columns; minimum is {}",
            raw.metrics.callable_columns, config.minimum_callable_bases
        )));
    }
    if raw.metrics.callable_identity < config.minimum_identity {
        return Err(Error::Alignment(format!(
            "alignment callable identity {:.4} is below {:.4}",
            raw.metrics.callable_identity, config.minimum_identity
        )));
    }
    let (segments, wraps_origin) = segments(raw, reference);
    let columns = raw
        .columns
        .iter()
        .map(|column| AlignmentColumn {
            query_base: column.query_base,
            reference_base: column.reference_base,
            original_call_index_0based: column
                .query_index
                .and_then(|index| selected.mapping.get(index).copied()),
            reference_index_0based: column
                .reference_index
                .map(|index| match reference.topology {
                    ReferenceTopology::Linear => index,
                    ReferenceTopology::Circular => index % reference.len(),
                }),
        })
        .collect();
    Ok(Alignment {
        orientation: selected.orientation,
        score: raw.score,
        reference_segments: segments,
        wraps_origin,
        metrics: raw.metrics.clone(),
        columns,
    })
}

fn retained_profiles(
    qc: &QualityControlResult,
    signal: &SignalAnalysis,
) -> Result<Vec<Option<EvidenceProfile>>> {
    if signal.loci.len() != qc.per_call.len() {
        return Err(Error::Alignment(format!(
            "signal/quality call count mismatch: {} loci, {} quality records",
            signal.loci.len(),
            qc.per_call.len()
        )));
    }
    if qc.trim_start_0based > qc.trim_end_0based_exclusive
        || qc.trim_end_0based_exclusive > signal.loci.len()
    {
        return Err(Error::Alignment(format!(
            "invalid trim interval {}..{} for {} locus profiles",
            qc.trim_start_0based,
            qc.trim_end_0based_exclusive,
            signal.loci.len()
        )));
    }
    let profiles = signal.loci[qc.trim_start_0based..qc.trim_end_0based_exclusive]
        .iter()
        .map(|locus| locus.profile)
        .collect::<Vec<_>>();
    if profiles.len() != qc.retained_sequence.len() {
        return Err(Error::Alignment(format!(
            "retained sequence/profile length mismatch: {} bases, {} profiles",
            qc.retained_sequence.len(),
            profiles.len()
        )));
    }
    Ok(profiles)
}

fn compare(left: &RawAlignment, right: &RawAlignment) -> Ordering {
    left.score.cmp(&right.score)
}

fn segments(alignment: &RawAlignment, reference: &Reference) -> (Vec<ReferenceSegment>, bool) {
    match reference.topology {
        ReferenceTopology::Linear => (
            vec![ReferenceSegment {
                start_0based: alignment.start_reference,
                end_0based_exclusive: alignment.end_reference,
            }],
            false,
        ),
        ReferenceTopology::Circular => {
            let length = reference.len();
            let start = alignment.start_reference % length;
            let span = alignment.end_reference - alignment.start_reference;
            let unwrapped_end = start + span;
            if unwrapped_end <= length {
                (
                    vec![ReferenceSegment {
                        start_0based: start,
                        end_0based_exclusive: unwrapped_end,
                    }],
                    false,
                )
            } else {
                (
                    vec![
                        ReferenceSegment {
                            start_0based: start,
                            end_0based_exclusive: length,
                        },
                        ReferenceSegment {
                            start_0based: 0,
                            end_0based_exclusive: unwrapped_end - length,
                        },
                    ],
                    true,
                )
            }
        }
    }
}
