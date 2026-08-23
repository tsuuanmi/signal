//! Compact typed assembly and deterministic JSON serialization.

use crate::config::Config;
use crate::error::Result;
use crate::model::alignment::Alignment;
use crate::model::basecalls::BaseCalls;
use crate::model::quality::QualityControlResult;
use crate::model::reference::Reference;
use crate::model::result::{
    AlignmentResult, AnalysisResult, IntervalResult, MetaResult, MethodsResult, ReferenceResult,
    SequenceResult, TraceResult, WarningSummaryResult,
};
use crate::model::trace::Chromatogram;
use crate::model::variant::VariantCallingResult;
use crate::report::variant;

/// Inputs consumed to build the immutable analysis document.
pub(crate) struct CompletedAnalysis {
    pub(crate) config: Config,
    pub(crate) trace: Chromatogram,
    pub(crate) reference: Reference,
    pub(crate) calls: BaseCalls,
    pub(crate) quality: QualityControlResult,
    pub(crate) alignment: Alignment,
    pub(crate) variants: VariantCallingResult,
}

/// Builds the compact v3 document without filesystem side effects.
pub(crate) fn build(completed: CompletedAnalysis) -> Result<AnalysisResult> {
    let CompletedAnalysis {
        config,
        trace,
        reference,
        calls,
        quality,
        alignment,
        variants,
    } = completed;
    let warnings = warning_summary(&calls, &alignment, variants.excluded_count());
    let variant_results = variant::project(variants.reported, &calls, &quality)?;
    let reference_segments = alignment
        .reference_segments
        .into_iter()
        .map(|segment| IntervalResult {
            start: segment.start_0based,
            end: segment.end_0based_exclusive,
        })
        .collect();

    Ok(AnalysisResult {
        schema_version: "signal.analysis/v3",
        meta: MetaResult {
            program: "signal",
            version: env!("CARGO_PKG_VERSION"),
            deterministic: true,
            input: TraceResult {
                file_name: trace.source_name,
                sha256: trace.source_sha256,
            },
            reference: ReferenceResult {
                name: reference.name,
                topology: reference.topology,
                sequence_sha256: reference.sequence_sha256,
            },
            configuration_sha256: config.source_sha256,
            methods: MethodsResult {
                basecalling: "signal.peak_recall/v2",
                quality_control: "signal.apollo_relative_quality/v1",
                trimming: "signal.apollo_end_trim/v1",
                alignment: "signal.gotoh_semiglobal/v1",
                variant_calling: "signal.primary_difference/v3",
            },
        },
        sequence: SequenceResult {
            primary: calls.primary_sequence,
            ambiguity: calls.ambiguity_sequence,
            retained: quality.retained_sequence,
            trim: IntervalResult {
                start: quality.trim_start_0based,
                end: quality.trim_end_0based_exclusive,
            },
        },
        alignment: AlignmentResult {
            orientation: alignment.orientation,
            score: alignment.score,
            metrics: alignment.metrics,
            reference_segments,
            wraps_origin: alignment.wraps_origin,
            operation_runs: alignment.operation_runs,
            gapped_query: alignment.gapped_query,
            gapped_reference: alignment.gapped_reference,
        },
        variants: variant_results,
        warnings,
    })
}

/// Serializes with a trailing newline for stable text files.
pub(crate) fn serialize(result: &AnalysisResult) -> Result<Vec<u8>> {
    let mut bytes = serde_json::to_vec_pretty(result)?;
    bytes.push(b'\n');
    Ok(bytes)
}

fn warning_summary(
    calls: &BaseCalls,
    alignment: &Alignment,
    excluded_variant_candidates: usize,
) -> WarningSummaryResult {
    let unresolved_primary_calls = calls
        .calls
        .iter()
        .filter(|call| call.primary == 'N')
        .count();
    let multi_channel_unresolved_calls = calls
        .calls
        .iter()
        .filter(|call| call.ambiguity == 'N' && call.qualifying_channels.len() > 2)
        .count();
    let vendor_disagreements = calls
        .calls
        .iter()
        .filter(|call| call.vendor_agrees == Some(false))
        .count();
    let reference_origin_wrap = alignment.wraps_origin;
    let total = unresolved_primary_calls
        + multi_channel_unresolved_calls
        + vendor_disagreements
        + excluded_variant_candidates
        + usize::from(reference_origin_wrap);
    WarningSummaryResult {
        total,
        unresolved_primary_calls,
        multi_channel_unresolved_calls,
        vendor_disagreements,
        excluded_variant_candidates,
        reference_origin_wrap,
    }
}
