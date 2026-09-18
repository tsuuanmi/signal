//! Projection of sample scientific evidence into the public JSON contract.

use crate::error::{Error, Result};
use crate::model::reference::Reference;
use crate::model::result::{IntervalResult, ReferenceResult};
use crate::model::sample_evidence::SampleEvidence;
use crate::model::sample_result::{
    SampleEvidenceResult, SampleLocusObservationResult, SampleLocusResult, SampleProvenanceResult,
    SampleReadAlignmentResult, SampleReadResult, SampleVariantCallResult, SampleVariantResult,
    SampleVariantSupportResult,
};

/// Inputs consumed to build one immutable sample-evidence document.
pub(crate) struct CompletedSampleEvidence {
    pub(crate) sample_id: String,
    pub(crate) reference: Reference,
    pub(crate) evidence: SampleEvidence,
}

/// Builds `signal.sample_evidence/v1` without filesystem side effects.
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

    let reads = evidence
        .reads
        .into_iter()
        .map(|read| SampleReadResult {
            name: read.input_name,
            sha256: read.input_sha256,
            alignment: SampleReadAlignmentResult {
                orientation: read.alignment.orientation,
                score: read.alignment.score,
                callable_bases: read.alignment.callable_bases,
                identity: read.alignment.identity,
                mismatches: read.alignment.mismatches,
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

    let loci = evidence
        .loci
        .into_iter()
        .map(|locus| SampleLocusResult {
            position: locus.position_1based,
            reference: locus.reference_base,
            observations: locus
                .observations
                .into_iter()
                .map(|observation| SampleLocusObservationResult {
                    read_name: observation.input_name,
                    read_sha256: observation.input_sha256,
                    orientation: observation.orientation,
                    state: observation.state,
                    base: observation.base,
                    index: observation.call_index_0based,
                    relative_quality: observation.relative_quality,
                })
                .collect(),
        })
        .collect();

    let variants = evidence
        .variants
        .into_iter()
        .map(|variant| SampleVariantResult {
            position: variant.position_1based,
            reference: variant.reference,
            alternate: variant.alternate,
            kind: variant.kind,
            support: variant
                .support
                .into_iter()
                .map(|support| SampleVariantSupportResult {
                    read_name: support.input_name,
                    read_sha256: support.input_sha256,
                    orientation: support.orientation,
                    eligible: support.eligible,
                    exclusion_reasons: support.exclusion_reasons,
                    calls: support
                        .calls
                        .into_iter()
                        .map(|call| SampleVariantCallResult {
                            role: call.role,
                            index: call.call_index_0based,
                            position: call.reference_position_1based,
                            ploc: call.ploc_0based,
                        })
                        .collect(),
                })
                .collect(),
        })
        .collect();

    Ok(SampleEvidenceResult {
        schema_version: "signal.sample_evidence/v1",
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
        loci,
        variants,
    })
}
