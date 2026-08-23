//! End-to-end scientific stage sequencing and operational stage logging.

use std::time::Instant;

use crate::alignment;
use crate::basecalling;
use crate::cli::AnalyzeArgs;
use crate::error::{Error, Result};
use crate::logger::Logger;
use crate::model::basecalls::PeakSource;
use crate::model::variant::VariantKind;
use crate::pipeline::input;
use crate::quality_control;
use crate::report::{self, CompletedAnalysis};
use crate::variant_calling;

/// Runs one complete AB1-to-JSON analysis with one per-trace append-only log.
pub(crate) fn run(args: &AnalyzeArgs) -> Result<()> {
    let trace_stem = input::trace_stem(&args.trace)?;
    let mut logger = Logger::open(trace_stem)?;
    let analysis_started = Instant::now();
    logger.info(
        module_path!(),
        line!(),
        format_args!(
            "event=analysis_started version={} trace_path={:?} reference_path={:?}",
            env!("CARGO_PKG_VERSION"),
            args.trace.display().to_string(),
            args.reference.display().to_string()
        ),
    )?;

    let mut stage = "input_loading";
    match run_logged(args, &mut logger, &mut stage, analysis_started) {
        Ok(()) => Ok(()),
        Err(analysis) => {
            let logging = logger
                .error(
                    module_path!(),
                    line!(),
                    format_args!(
                        "event=analysis_failed stage={stage} elapsed_ms={} error={:?}",
                        analysis_started.elapsed().as_millis(),
                        analysis.to_string()
                    ),
                )
                .and_then(|()| logger.sync());
            match logging {
                Ok(()) => Err(analysis),
                Err(logging) => Err(Error::AnalysisAndLog {
                    analysis: Box::new(analysis),
                    logging: Box::new(logging),
                }),
            }
        }
    }
}

fn run_logged(
    args: &AnalyzeArgs,
    logger: &mut Logger,
    stage: &mut &'static str,
    analysis_started: Instant,
) -> Result<()> {
    *stage = "input_loading";
    let stage_started = Instant::now();
    let inputs = input::load(args)?;
    logger.info(
        module_path!(),
        line!(),
        format_args!(
            concat!(
                "event=inputs_loaded elapsed_ms={} trace_name={:?} trace_sha256={} ",
                "samples={} call_loci={} vendor_primary={} vendor_quality={} ",
                "reference_name={:?} reference_sha256={} topology={:?} reference_bases={} ",
                "config_path={:?} config_sha256={} output_path={:?}"
            ),
            stage_started.elapsed().as_millis(),
            inputs.trace.source_name,
            inputs.trace.source_sha256,
            inputs.trace.sample_count(),
            inputs.trace.call_count(),
            inputs.trace.vendor.primary.is_some(),
            inputs.trace.vendor.qualities.is_some(),
            inputs.reference.name,
            inputs.reference.sequence_sha256,
            inputs.reference.topology,
            inputs.reference.len(),
            inputs.config.source_path.display().to_string(),
            inputs.config.source_sha256,
            inputs.output.display().to_string()
        ),
    )?;

    *stage = "basecalling";
    let stage_started = Instant::now();
    let calls = basecalling::call(&inputs.trace, &inputs.config.basecalling)?;
    let canonical_primary = calls
        .calls
        .iter()
        .filter(|call| call.primary != 'N')
        .count();
    let unresolved_primary = calls.len() - canonical_primary;
    let two_channel_iupac = calls
        .calls
        .iter()
        .filter(|call| call.qualifying_channels.len() == 2 && call.ambiguity != 'N')
        .count();
    let multi_channel_unresolved = calls
        .calls
        .iter()
        .filter(|call| call.qualifying_channels.len() > 2 && call.ambiguity == 'N')
        .count();
    let calls_with_fallback = calls
        .calls
        .iter()
        .filter(|call| {
            call.peaks
                .iter()
                .any(|peak| peak.source == PeakSource::PlocFallback)
        })
        .count();
    let vendor_compared = calls
        .calls
        .iter()
        .filter(|call| call.vendor_agrees.is_some())
        .count();
    let vendor_disagreements = calls
        .calls
        .iter()
        .filter(|call| call.vendor_agrees == Some(false))
        .count();
    logger.info(
        module_path!(),
        line!(),
        format_args!(
            concat!(
                "event=basecalling_completed elapsed_ms={} calls={} canonical_primary={} ",
                "unresolved_primary={} two_channel_iupac={} multi_channel_unresolved={} ",
                "calls_with_ploc_fallback={} vendor_compared={} vendor_disagreements={} ",
                "secondary_peak_ratio={:.4}"
            ),
            stage_started.elapsed().as_millis(),
            calls.len(),
            canonical_primary,
            unresolved_primary,
            two_channel_iupac,
            multi_channel_unresolved,
            calls_with_fallback,
            vendor_compared,
            vendor_disagreements,
            inputs.config.basecalling.secondary_peak_ratio
        ),
    )?;

    *stage = "quality_control";
    let stage_started = Instant::now();
    let quality = quality_control::analyze(&inputs.trace, &calls, &inputs.config.quality_control)?;
    let score_min = quality
        .per_call
        .iter()
        .map(|quality| quality.relative_quality_score)
        .min()
        .unwrap_or(0);
    let score_max = quality
        .per_call
        .iter()
        .map(|quality| quality.relative_quality_score)
        .max()
        .unwrap_or(0);
    let score_mean = if quality.per_call.is_empty() {
        0.0
    } else {
        quality
            .per_call
            .iter()
            .map(|quality| u64::from(quality.relative_quality_score))
            .sum::<u64>() as f64
            / quality.per_call.len() as f64
    };
    let max_penalty = quality
        .per_call
        .iter()
        .map(|quality| quality.penalty)
        .max()
        .unwrap_or(0);
    let vendor_quality_applicable = quality
        .per_call
        .iter()
        .filter(|quality| quality.vendor_quality_applies)
        .count();
    let trimmed_left = quality.trim_start_0based;
    let trimmed_right = calls
        .len()
        .saturating_sub(quality.trim_end_0based_exclusive);
    let retained_fraction = quality.retained_sequence.len() as f64 / calls.len() as f64;
    logger.info(
        module_path!(),
        line!(),
        format_args!(
            concat!(
                "event=quality_control_completed elapsed_ms={} trim={}..{} retained={} ",
                "trimmed_left={} trimmed_right={} retained_fraction={:.4} ",
                "relative_score_min={} relative_score_mean={:.2} relative_score_max={} ",
                "max_penalty={} vendor_quality_applicable={}"
            ),
            stage_started.elapsed().as_millis(),
            quality.trim_start_0based,
            quality.trim_end_0based_exclusive,
            quality.retained_sequence.len(),
            trimmed_left,
            trimmed_right,
            retained_fraction,
            score_min,
            score_mean,
            score_max,
            max_penalty,
            vendor_quality_applicable
        ),
    )?;

    *stage = "alignment";
    let stage_started = Instant::now();
    let alignment = alignment::align_best(&quality, &inputs.reference, &inputs.config.alignment)?;
    let reference_segments = alignment
        .reference_segments
        .iter()
        .map(|segment| format!("{}..{}", segment.start_0based, segment.end_0based_exclusive))
        .collect::<Vec<_>>()
        .join(",");
    logger.info(
        module_path!(),
        line!(),
        format_args!(
            concat!(
                "event=alignment_completed elapsed_ms={} orientation={:?} score={} ",
                "exact_matches={} mismatches={} gap_opens={} callable_columns={} ",
                "callable_identity={:.4} unresolved_query_bases={} segments={} ",
                "segment_bounds={:?} wraps_origin={}"
            ),
            stage_started.elapsed().as_millis(),
            alignment.orientation,
            alignment.score,
            alignment.metrics.exact_matches,
            alignment.metrics.mismatches,
            alignment.metrics.gap_opens,
            alignment.metrics.callable_columns,
            alignment.metrics.callable_identity,
            alignment.metrics.unresolved_query_bases,
            alignment.reference_segments.len(),
            reference_segments,
            alignment.wraps_origin
        ),
    )?;

    *stage = "variant_calling";
    let stage_started = Instant::now();
    let variants = variant_calling::call(
        &alignment,
        &inputs.reference,
        &calls,
        &quality,
        &inputs.config.variant_calling,
    )?;
    let snvs = variants
        .reported
        .iter()
        .filter(|variant| variant.kind == VariantKind::Snv)
        .count();
    let insertions = variants
        .reported
        .iter()
        .filter(|variant| variant.kind == VariantKind::Ins)
        .count();
    let deletions = variants
        .reported
        .iter()
        .filter(|variant| variant.kind == VariantKind::Del)
        .count();
    logger.info(
        module_path!(),
        line!(),
        format_args!(
            concat!(
                "event=variant_calling_completed elapsed_ms={} reported={} snv={} insertion={} ",
                "deletion={} excluded={} region_count={} minimum_peak_height={} ",
                "relative_quality_threshold={} max_indel_length={}"
            ),
            stage_started.elapsed().as_millis(),
            variants.reported.len(),
            snvs,
            insertions,
            deletions,
            variants.excluded_count(),
            inputs.config.variant_calling.regions.len(),
            inputs.config.variant_calling.minimum_peak_height,
            inputs.config.variant_calling.relative_quality_threshold,
            inputs.config.variant_calling.max_indel_length
        ),
    )?;
    for excluded in &variants.excluded {
        let position = excluded
            .position_1based
            .map_or_else(|| "unknown".to_owned(), |position| position.to_string());
        let reasons = excluded
            .reasons
            .iter()
            .map(|reason| reason.label())
            .collect::<Vec<_>>()
            .join(",");
        logger.warn(
            module_path!(),
            line!(),
            format_args!(
                "event=variant_removed kind={} contig={:?} position={} reasons={}",
                excluded.kind.label(),
                excluded.contig,
                position,
                reasons
            ),
        )?;
    }

    *stage = "reporting";
    let stage_started = Instant::now();
    let output = inputs.output.clone();
    let result = report::build(CompletedAnalysis {
        config: inputs.config,
        trace: inputs.trace,
        reference: inputs.reference,
        calls,
        quality,
        alignment,
        variants,
    })?;
    if result.warnings.total > 0 {
        logger.warn(
            module_path!(),
            line!(),
            format_args!(
                concat!(
                    "event=warning_summary total={} unresolved_primary_calls={} ",
                    "multi_channel_unresolved_calls={} vendor_disagreements={} ",
                    "excluded_variant_candidates={} reference_origin_wrap={}"
                ),
                result.warnings.total,
                result.warnings.unresolved_primary_calls,
                result.warnings.multi_channel_unresolved_calls,
                result.warnings.vendor_disagreements,
                result.warnings.excluded_variant_candidates,
                result.warnings.reference_origin_wrap
            ),
        )?;
    }
    let result_variants = result.variants.len();
    let schema_version = result.schema_version;
    let bytes = report::serialize(&result)?;

    *stage = "result_publication";
    logger.info(
        module_path!(),
        line!(),
        format_args!(
            concat!(
                "event=result_ready_for_publication elapsed_ms={} total_elapsed_ms={} ",
                "schema={} variants={} warnings={} output_path={:?} bytes={}"
            ),
            stage_started.elapsed().as_millis(),
            analysis_started.elapsed().as_millis(),
            schema_version,
            result_variants,
            result.warnings.total,
            output.display().to_string(),
            bytes.len()
        ),
    )?;
    logger.sync()?;
    report::publish(&output, &bytes)
}
