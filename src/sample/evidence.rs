//! Deterministic aggregation of read observations into coordinate/variant evidence.

use std::collections::{BTreeMap, BTreeSet};

use crate::error::{Error, Result};
use crate::model::alignment::AlignmentColumn;
use crate::model::read_observation::ReadObservation;
use crate::model::sample_evidence::{
    LocusEvidence, LocusObservation, LocusState, SampleEvidence, SampleReadAlignmentEvidence,
    SampleReadEvidence, VariantCallEvidence, VariantEvidence, VariantSupport,
};
use crate::model::variant::{VariantCallMapping, VariantKind};

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
struct VariantKey {
    position_1based: usize,
    reference: String,
    alternate: String,
    kind: VariantKind,
}

struct LocusBuilder {
    reference_base: char,
    observations: Vec<LocusObservation>,
}

/// Aggregates independently processed reads without using filenames or pair labels as merge keys.
pub(crate) fn aggregate(reads: &[ReadObservation]) -> Result<SampleEvidence> {
    let first = reads
        .first()
        .ok_or_else(|| Error::Sample("at least one read observation is required".into()))?;
    let reference_sha256 = first.reference_sha256.clone();
    let configuration_sha256 = first.configuration_sha256.clone();

    let mut identities = BTreeSet::new();
    let mut placements = Vec::with_capacity(reads.len());
    let mut loci: BTreeMap<usize, LocusBuilder> = BTreeMap::new();
    let mut variants: BTreeMap<VariantKey, Vec<VariantSupport>> = BTreeMap::new();

    for read in reads {
        if read.reference_sha256 != reference_sha256 {
            return Err(Error::Sample(
                "all reads must use the same reference identity".into(),
            ));
        }
        if read.configuration_sha256 != configuration_sha256 {
            return Err(Error::Sample(
                "all reads must use the same scientific configuration identity".into(),
            ));
        }
        if !identities.insert(read.input_sha256.clone()) {
            return Err(Error::Sample(
                "duplicate input trace content cannot contribute twice".into(),
            ));
        }

        placements.push(SampleReadEvidence {
            input_name: read.input_name.clone(),
            input_sha256: read.input_sha256.clone(),
            alignment: SampleReadAlignmentEvidence {
                orientation: read.alignment.orientation,
                callable_bases: read.alignment.metrics.callable_columns,
                identity: read.alignment.metrics.callable_identity,
                gap_opens: read.alignment.metrics.gap_opens,
                unresolved_bases: read.alignment.metrics.unresolved_query_bases,
                reference_segments: read.alignment.reference_segments.clone(),
                wraps_origin: read.alignment.wraps_origin,
            },
        });

        for column in &read.alignment.columns {
            let Some(reference_index_0based) = column.reference_index_0based else {
                continue;
            };
            let position_1based = reference_index_0based
                .checked_add(1)
                .ok_or_else(|| Error::Sample("reference coordinate overflow".into()))?;
            let observation = locus_observation(read, column)?;
            let entry = loci.entry(position_1based).or_insert_with(|| LocusBuilder {
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

        for observed in &read.variants.observed {
            let variant = &observed.variant;
            let key = VariantKey {
                position_1based: variant.position_1based,
                reference: variant.reference.clone(),
                alternate: variant.alternate.clone(),
                kind: variant.kind,
            };
            variants.entry(key).or_default().push(VariantSupport {
                input_name: read.input_name.clone(),
                input_sha256: read.input_sha256.clone(),
                orientation: read.alignment.orientation,
                eligible: observed.eligible(),
                exclusion_reasons: observed.exclusion_reasons.clone(),
                calls: variant_calls(read, &variant.calls)?,
            });
        }
    }

    placements.sort_by(|left, right| left.input_sha256.cmp(&right.input_sha256));

    let loci = loci
        .into_iter()
        .map(|(position_1based, mut built)| {
            built
                .observations
                .sort_by(|left, right| left.input_sha256.cmp(&right.input_sha256));
            LocusEvidence {
                position_1based,
                reference_base: built.reference_base,
                observations: built.observations,
            }
        })
        .collect();

    let variants = variants
        .into_iter()
        .map(|(key, mut support)| {
            support.sort_by(|left, right| left.input_sha256.cmp(&right.input_sha256));
            support.dedup_by(|left, right| left.input_sha256 == right.input_sha256);
            VariantEvidence {
                position_1based: key.position_1based,
                reference: key.reference,
                alternate: key.alternate,
                kind: key.kind,
                support,
            }
        })
        .collect();

    Ok(SampleEvidence {
        reference_sha256,
        configuration_sha256,
        reads: placements,
        loci,
        variants,
    })
}

fn variant_calls(
    read: &ReadObservation,
    mappings: &[VariantCallMapping],
) -> Result<Vec<VariantCallEvidence>> {
    mappings
        .iter()
        .map(|mapping| {
            let call = read
                .calls
                .calls
                .get(mapping.call_index_0based)
                .ok_or_else(|| {
                    Error::Sample(format!(
                        "variant references missing call index {}",
                        mapping.call_index_0based
                    ))
                })?;
            if call.index_0based != mapping.call_index_0based {
                return Err(Error::Sample(format!(
                    "variant call index {} does not match base-call record",
                    mapping.call_index_0based
                )));
            }
            let reference_position_1based = mapping
                .reference_position_0based
                .map(|position| {
                    position
                        .checked_add(1)
                        .ok_or_else(|| Error::Sample("reference coordinate overflow".into()))
                })
                .transpose()?;
            Ok(VariantCallEvidence {
                role: mapping.role,
                call_index_0based: mapping.call_index_0based,
                reference_position_1based,
                ploc_0based: call.ploc_0based,
            })
        })
        .collect()
}

fn locus_observation(read: &ReadObservation, column: &AlignmentColumn) -> Result<LocusObservation> {
    if column.reference_base == '-' {
        return Err(Error::Sample(
            "reference-coordinate locus cannot contain an insertion column".into(),
        ));
    }
    if column.query_base == '-' {
        return Ok(LocusObservation {
            input_name: read.input_name.clone(),
            input_sha256: read.input_sha256.clone(),
            orientation: read.alignment.orientation,
            state: LocusState::Deletion,
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

    let state = if !is_canonical(column.query_base) || !is_canonical(column.reference_base) {
        LocusState::Unresolved
    } else if column.query_base == column.reference_base {
        LocusState::Reference
    } else {
        LocusState::Alternate
    };

    Ok(LocusObservation {
        input_name: read.input_name.clone(),
        input_sha256: read.input_sha256.clone(),
        orientation: read.alignment.orientation,
        state,
        base: Some(column.query_base),
        call_index_0based: Some(call_index_0based),
        relative_quality: Some(quality.relative_quality_score),
    })
}

const fn is_canonical(base: char) -> bool {
    matches!(base, 'A' | 'C' | 'G' | 'T')
}

#[cfg(test)]
mod tests {
    use crate::model::alignment::{
        Alignment, AlignmentColumn, AlignmentMetrics, Orientation, ReferenceSegment,
    };
    use crate::model::basecalls::{BaseCall, BaseCalls, ChannelPeak, PeakSource};
    use crate::model::nucleotide::Nucleotide;
    use crate::model::quality::{CallQuality, QualityControlResult};
    use crate::model::read_observation::ReadObservation;
    use crate::model::signal::SignalAnalysis;
    use crate::model::variant::{
        ObservedVariant, Variant, VariantCallMapping, VariantCallRole, VariantCallingResult,
        VariantExclusionReason, VariantKind,
    };

    use super::*;

    fn observation(
        input_sha256: &str,
        reference_sha256: &str,
        configuration_sha256: &str,
        orientation: Orientation,
        columns: Vec<AlignmentColumn>,
        variants: Vec<Variant>,
    ) -> ReadObservation {
        let call_count = columns
            .iter()
            .filter_map(|column| column.original_call_index_0based)
            .max()
            .map_or(0, |index| index + 1);
        let per_call = (0..call_count)
            .map(|index_0based| CallQuality {
                index_0based,
                penalty: 0,
                relative_quality_score: 50,
                vendor_quality_applies: false,
            })
            .collect();
        let observed = variants
            .iter()
            .cloned()
            .map(|variant| ObservedVariant {
                variant,
                exclusion_reasons: Vec::new(),
            })
            .collect();
        ReadObservation {
            input_name: format!("{input_sha256}.ab1"),
            input_sha256: input_sha256.into(),
            reference_sha256: reference_sha256.into(),
            configuration_sha256: configuration_sha256.into(),
            calls: BaseCalls {
                calls: (0..call_count)
                    .map(|index_0based| BaseCall {
                        index_0based,
                        ploc_0based: index_0based * 10,
                        window_start_0based: index_0based * 10,
                        window_end_0based_exclusive: index_0based * 10 + 1,
                        peaks: Nucleotide::ALL.map(|base| ChannelPeak {
                            base,
                            height: 100,
                            position_0based: index_0based * 10,
                            source: PeakSource::LocalMaximum,
                        }),
                        primary_peak_evidence: None,
                        primary: 'G',
                        ambiguity: 'G',
                        qualifying_channels: vec![Nucleotide::G],
                        vendor_agrees: None,
                    })
                    .collect(),
                primary_sequence: "G".repeat(call_count),
            },
            signal: SignalAnalysis {
                call_metrics: Vec::new(),
                windows: Vec::new(),
                noisy_regions: Vec::new(),
            },
            quality: QualityControlResult {
                per_call,
                trim_start_0based: 0,
                trim_end_0based_exclusive: call_count,
                retained_sequence: String::new(),
            },
            alignment: Alignment {
                orientation,
                score: 1,
                reference_segments: vec![ReferenceSegment {
                    start_0based: 0,
                    end_0based_exclusive: 10,
                }],
                wraps_origin: false,
                metrics: AlignmentMetrics {
                    exact_matches: 0,
                    mismatches: 0,
                    gap_opens: 0,
                    callable_columns: 0,
                    callable_identity: 0.0,
                    unresolved_query_bases: 0,
                },
                columns,
            },
            variants: VariantCallingResult {
                reported: variants,
                observed,
                excluded: Vec::new(),
            },
        }
    }

    fn column(
        query_base: char,
        reference_base: char,
        call: Option<usize>,
        reference: usize,
    ) -> AlignmentColumn {
        AlignmentColumn {
            query_base,
            reference_base,
            original_call_index_0based: call,
            reference_index_0based: Some(reference),
        }
    }

    fn snv(position_1based: usize, reference: &str, alternate: &str) -> Variant {
        Variant {
            contig: "reference".into(),
            position_1based,
            reference: reference.into(),
            alternate: alternate.into(),
            kind: VariantKind::Snv,
            calls: vec![VariantCallMapping {
                role: VariantCallRole::Supporting,
                call_index_0based: 0,
                reference_position_0based: Some(position_1based - 1),
            }],
        }
    }

    #[test]
    fn aggregates_reference_coordinate_observations_and_normalized_variants() -> Result<()> {
        let forward = observation(
            "a",
            "reference",
            "config",
            Orientation::Forward,
            vec![column('G', 'A', Some(0), 72)],
            vec![snv(73, "A", "G")],
        );
        let reverse = observation(
            "b",
            "reference",
            "config",
            Orientation::Reverse,
            vec![column('G', 'A', Some(0), 72)],
            vec![snv(73, "A", "G")],
        );

        let evidence = aggregate(&[reverse, forward])?;

        assert_eq!(evidence.reads.len(), 2);
        assert_eq!(evidence.reads[0].input_name, "a.ab1");
        assert_eq!(evidence.loci.len(), 1);
        assert_eq!(evidence.loci[0].position_1based, 73);
        assert_eq!(evidence.loci[0].observations.len(), 2);
        assert_eq!(evidence.loci[0].observations[0].input_name, "a.ab1");
        assert!(
            evidence.loci[0]
                .observations
                .iter()
                .all(|item| item.state == LocusState::Alternate && item.base == Some('G'))
        );
        assert_eq!(evidence.variants.len(), 1);
        assert_eq!(evidence.variants[0].support.len(), 2);
        assert_eq!(evidence.variants[0].support[0].input_name, "a.ab1");
        assert_eq!(evidence.variants[0].support[0].calls.len(), 1);
        assert_eq!(
            evidence.variants[0].support[0].calls[0].role,
            VariantCallRole::Supporting
        );
        assert_eq!(
            evidence.variants[0].support[0].calls[0].call_index_0based,
            0
        );
        assert_eq!(
            evidence.variants[0].support[0].calls[0].reference_position_1based,
            Some(73)
        );
        assert_eq!(evidence.variants[0].support[0].calls[0].ploc_0based, 0);
        assert_eq!(evidence.reads[0].alignment.callable_bases, 0);
        Ok(())
    }

    #[test]
    fn preserves_filtered_variant_observation_without_reporting_it() -> Result<()> {
        let variant = snv(73, "A", "G");
        let forward = observation(
            "a",
            "reference",
            "config",
            Orientation::Forward,
            vec![column('G', 'A', Some(0), 72)],
            vec![variant.clone()],
        );
        let mut reverse = observation(
            "b",
            "reference",
            "config",
            Orientation::Reverse,
            vec![column('G', 'A', Some(0), 72)],
            vec![variant],
        );
        reverse.variants.reported.clear();
        reverse.variants.observed[0].exclusion_reasons =
            vec![VariantExclusionReason::PeakBelowMinimum];

        let evidence = aggregate(&[forward, reverse])?;

        assert_eq!(evidence.variants.len(), 1);
        assert_eq!(evidence.variants[0].support.len(), 2);
        assert_eq!(evidence.variants[0].support[0].input_sha256, "a");
        assert!(evidence.variants[0].support[0].eligible);
        assert!(evidence.variants[0].support[0].exclusion_reasons.is_empty());
        assert_eq!(evidence.variants[0].support[1].input_sha256, "b");
        assert!(!evidence.variants[0].support[1].eligible);
        assert_eq!(
            evidence.variants[0].support[1].exclusion_reasons,
            vec![VariantExclusionReason::PeakBelowMinimum]
        );
        Ok(())
    }

    #[test]
    fn missing_locus_coverage_is_not_reference_support() -> Result<()> {
        let first = observation(
            "a",
            "reference",
            "config",
            Orientation::Forward,
            vec![column('A', 'A', Some(0), 10)],
            Vec::new(),
        );
        let second = observation(
            "b",
            "reference",
            "config",
            Orientation::Reverse,
            vec![column('C', 'C', Some(0), 20)],
            Vec::new(),
        );

        let evidence = aggregate(&[first, second])?;

        assert_eq!(evidence.loci.len(), 2);
        assert_eq!(evidence.loci[0].observations.len(), 1);
        assert_eq!(evidence.loci[1].observations.len(), 1);
        Ok(())
    }

    #[test]
    fn preserves_unresolved_and_deletion_states() -> Result<()> {
        let read = observation(
            "a",
            "reference",
            "config",
            Orientation::Forward,
            vec![column('N', 'A', Some(0), 10), column('-', 'C', None, 11)],
            Vec::new(),
        );

        let evidence = aggregate(&[read])?;

        assert_eq!(
            evidence.loci[0].observations[0].state,
            LocusState::Unresolved
        );
        assert_eq!(evidence.loci[1].observations[0].state, LocusState::Deletion);
        assert_eq!(evidence.loci[1].observations[0].base, None);
        Ok(())
    }

    #[test]
    fn rejects_incompatible_or_duplicate_reads() {
        let first = observation(
            "a",
            "reference",
            "config",
            Orientation::Forward,
            vec![column('A', 'A', Some(0), 0)],
            Vec::new(),
        );
        let incompatible = observation(
            "b",
            "other-reference",
            "config",
            Orientation::Forward,
            vec![column('A', 'A', Some(0), 0)],
            Vec::new(),
        );
        assert!(aggregate(&[first.clone(), incompatible]).is_err());

        let mut duplicate = observation(
            "a",
            "reference",
            "config",
            Orientation::Reverse,
            vec![column('A', 'A', Some(0), 0)],
            Vec::new(),
        );
        duplicate.input_name = "renamed-copy.ab1".into();
        assert!(aggregate(&[first, duplicate]).is_err());
    }
}
