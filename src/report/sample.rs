//! Projection of compact sample scientific evidence into the public JSON contract.

use std::collections::BTreeSet;
use std::path::Path;

use crate::error::{Error, Result};
use crate::model::reference::Reference;
use crate::model::result::{AlignmentResult, IntervalResult, PeakHeightsResult, ReferenceResult};
use crate::model::sample_evidence::SampleEvidence;
use crate::model::sample_result::{
    SampleCoverageResult, SampleEvidenceResult, SampleLocusDifferenceObservationResult,
    SampleLocusDifferenceResult, SampleOverlapResult, SampleProvenanceResult, SampleReadResult,
    SampleVariantCallResult, SampleVariantResult, SampleVariantSupportResult,
};

/// Inputs consumed to build one immutable sample-evidence document.
pub(crate) struct CompletedSampleEvidence {
    pub(crate) sample_id: String,
    pub(crate) reference: Reference,
    pub(crate) evidence: SampleEvidence,
}

/// Builds `signal.sample_evidence/v6` without filesystem side effects.
pub(crate) fn build(completed: CompletedSampleEvidence) -> Result<SampleEvidenceResult> {
    let CompletedSampleEvidence {
        sample_id,
        reference,
        evidence,
    } = completed;
    if evidence.reference_sha256 != reference.sequence_sha256 {
        return Err(Error::Report(
            "sample evidence reference identity does not match report reference".into(),
        ));
    }

    let read_names = reviewer_read_names(&evidence)?;
    let reads = evidence
        .reads
        .into_iter()
        .zip(read_names.iter())
        .map(|(read, name)| SampleReadResult {
            name: name.clone(),
            sha256: read.input_sha256,
            integrity: crate::report::signal::project_integrity(&read.integrity),
            alignment: AlignmentResult {
                orientation: read.alignment.orientation,
                callable_bases: read.alignment.callable_bases,
                identity: read.alignment.identity,
                gap_opens: read.alignment.gap_opens,
                unresolved_bases: read.alignment.unresolved_bases,
                reference_segments: read
                    .alignment
                    .reference_segments
                    .into_iter()
                    .map(|segment| IntervalResult {
                        start: segment.start_0based,
                        end: segment.end_0based_exclusive,
                    })
                    .collect(),
                wraps_origin: read.alignment.wraps_origin,
            },
        })
        .collect();

    let coverage = evidence
        .coverage
        .into_iter()
        .map(|segment| SampleCoverageResult {
            reference: IntervalResult {
                start: segment.start_0based,
                end: segment.end_0based_exclusive,
            },
            read_depth: segment.read_depth,
            forward_depth: segment.forward_depth,
            reverse_depth: segment.reverse_depth,
        })
        .collect();

    let overlaps = evidence
        .overlaps
        .into_iter()
        .map(|overlap| {
            Ok(SampleOverlapResult {
                left: read_name(&read_names, overlap.left_read_index)?.into(),
                right: read_name(&read_names, overlap.right_read_index)?.into(),
                shared_positions: overlap.shared_positions,
                comparable_bases: overlap.comparable_bases,
                agreements: overlap.agreements,
                conflicts: overlap.conflicts,
                agreement: overlap.agreement,
                eligible: overlap.eligible,
                exclusion_reasons: overlap.exclusion_reasons,
            })
        })
        .collect::<Result<Vec<_>>>()?;

    let locus_differences = evidence
        .locus_differences
        .into_iter()
        .map(|difference| {
            let observations = difference
                .observations
                .into_iter()
                .map(|observation| {
                    Ok(SampleLocusDifferenceObservationResult {
                        read: read_name(&read_names, observation.read_index)?.into(),
                        state: observation.state,
                        base: observation.base,
                        quality: observation.quality,
                    })
                })
                .collect::<Result<Vec<_>>>()?;
            Ok(SampleLocusDifferenceResult {
                position: difference.position_1based,
                reference: difference.reference_base,
                observations,
            })
        })
        .collect::<Result<Vec<_>>>()?;

    let variants = evidence
        .variants
        .into_iter()
        .map(|variant| {
            let support = variant
                .support
                .into_iter()
                .map(|support| {
                    Ok(SampleVariantSupportResult {
                        read: read_name(&read_names, support.read_index)?.into(),
                        eligible: support.eligible,
                        exclusion_reasons: support.exclusion_reasons,
                        calls: support
                            .calls
                            .into_iter()
                            .map(|call| SampleVariantCallResult {
                                role: call.role,
                                base: call.base,
                                peaks: PeakHeightsResult::from(call.peak_heights),
                                quality: call.quality,
                            })
                            .collect(),
                    })
                })
                .collect::<Result<Vec<_>>>()?;
            Ok(SampleVariantResult {
                position: variant.position_1based,
                reference: variant.reference,
                alternate: variant.alternate,
                kind: variant.kind,
                support,
            })
        })
        .collect::<Result<Vec<_>>>()?;

    Ok(SampleEvidenceResult {
        schema_version: "signal.sample_evidence/v6",
        sample_id,
        provenance: SampleProvenanceResult {
            reference: ReferenceResult {
                name: reference.name,
                topology: reference.topology,
                sha256: reference.sequence_sha256,
            },
            configuration_sha256: evidence.configuration_sha256,
        },
        reads,
        coverage,
        overlaps,
        locus_differences,
        variants,
    })
}

fn reviewer_read_names(evidence: &SampleEvidence) -> Result<Vec<String>> {
    let mut names = Vec::with_capacity(evidence.reads.len());
    let mut unique = BTreeSet::new();
    for read in &evidence.reads {
        let name = Path::new(&read.input_name)
            .file_stem()
            .and_then(|value| value.to_str())
            .filter(|value| !value.is_empty())
            .ok_or_else(|| Error::Report("sample read has no valid UTF-8 filename stem".into()))?
            .to_owned();
        if !unique.insert(name.clone()) {
            return Err(Error::Report(format!(
                "sample read name {name:?} is not unique"
            )));
        }
        names.push(name);
    }
    Ok(names)
}

fn read_name(read_names: &[String], index: usize) -> Result<&str> {
    read_names
        .get(index)
        .map(String::as_str)
        .ok_or_else(|| Error::Report(format!("sample evidence references missing read {index}")))
}
