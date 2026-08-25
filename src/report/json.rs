//! Compact typed assembly and deterministic JSON serialization.

use crate::config::Config;
use crate::error::Result;
use crate::model::alignment::Alignment;
use crate::model::basecalls::BaseCalls;
use crate::model::quality::QualityControlResult;
use crate::model::reference::Reference;
use crate::model::result::{
    AlignmentResult, AnalysisResult, InputResult, IntervalResult, ProvenanceResult, ReadResult,
    ReferenceResult, WarningSummaryResult,
};
use crate::model::signal::SignalAnalysis;
use crate::model::trace::Chromatogram;
use crate::model::variant::VariantCallingResult;
use crate::report::{signal, variant};

/// Inputs consumed to build the immutable analysis document.
pub(crate) struct CompletedAnalysis {
    pub(crate) config: Config,
    pub(crate) trace: Chromatogram,
    pub(crate) reference: Reference,
    pub(crate) calls: BaseCalls,
    pub(crate) signal: SignalAnalysis,
    pub(crate) quality: QualityControlResult,
    pub(crate) alignment: Alignment,
    pub(crate) variants: VariantCallingResult,
}

/// Builds the compact v5 document without filesystem side effects.
pub(crate) fn build_analysis(completed: CompletedAnalysis) -> Result<AnalysisResult> {
    let CompletedAnalysis {
        config,
        trace,
        reference,
        calls,
        signal,
        quality,
        alignment,
        variants,
    } = completed;
    let warnings = warning_summary(&calls, variants.excluded_count());
    let variant_results = variant::project(variants.reported, &calls, &quality)?;
    let signal_quality = signal::project(signal);
    let reference_segments = alignment
        .reference_segments
        .into_iter()
        .map(|segment| IntervalResult {
            start: segment.start_0based,
            end: segment.end_0based_exclusive,
        })
        .collect();

    Ok(AnalysisResult {
        schema_version: "signal.analysis/v5",
        provenance: ProvenanceResult {
            software_version: env!("CARGO_PKG_VERSION"),
            input: InputResult {
                sha256: trace.source_sha256,
            },
            reference: ReferenceResult {
                name: reference.name,
                topology: reference.topology,
                sha256: reference.sequence_sha256,
            },
            configuration_sha256: config.source_sha256,
        },
        read: ReadResult {
            call_count: calls.len(),
            trim: IntervalResult {
                start: quality.trim_start_0based,
                end: quality.trim_end_0based_exclusive,
            },
        },
        signal_quality,
        alignment: AlignmentResult {
            orientation: alignment.orientation,
            callable_bases: alignment.metrics.callable_columns,
            identity: alignment.metrics.callable_identity,
            unresolved_bases: alignment.metrics.unresolved_query_bases,
            gap_opens: alignment.metrics.gap_opens,
            reference_segments,
            wraps_origin: alignment.wraps_origin,
        },
        variants: variant_results,
        warnings,
    })
}

/// Serializes any typed result with a trailing newline for stable text files.
pub(crate) fn serialize<T: serde::Serialize>(result: &T) -> Result<Vec<u8>> {
    let mut bytes = serde_json::to_vec_pretty(result)?;
    bytes.push(b'\n');
    Ok(bytes)
}

fn warning_summary(calls: &BaseCalls, excluded_variant_candidates: usize) -> WarningSummaryResult {
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
    WarningSummaryResult {
        unresolved_primary_calls,
        multi_channel_unresolved_calls,
        excluded_variant_candidates,
    }
}
