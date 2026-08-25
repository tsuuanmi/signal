//! End-to-end scientific stage sequencing and operational stage logging.

use std::time::Instant;

use crate::alignment;
use crate::cli::AnalyzeArgs;
use crate::error::Result;
use crate::logger::Logger;
use crate::model::variant::VariantKind;
use crate::pipeline::read::ProcessedRead;
use crate::pipeline::{input, read};
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
        Err(error) => Err(super::record_failure(
            &mut logger,
            "analysis_failed",
            stage,
            analysis_started,
            error,
        )),
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
    let inputs = input::load_analysis(args)?;
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

    let ProcessedRead {
        calls,
        signal,
        quality,
        warnings: read_warnings,
    } = read::process(&inputs.trace, &inputs.config, logger, stage)?;

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

    let excluded_variant_candidates = variants.excluded_count();
    let reference_origin_wrap = alignment.wraps_origin;
    let warning_total = read_warnings.unresolved_primary_calls
        + read_warnings.multi_channel_unresolved_calls
        + read_warnings.vendor_disagreements
        + excluded_variant_candidates
        + usize::from(reference_origin_wrap);

    *stage = "reporting";
    let stage_started = Instant::now();
    let output = inputs.output.clone();
    let result = report::build_analysis(CompletedAnalysis {
        config: inputs.config,
        trace: inputs.trace,
        reference: inputs.reference,
        calls,
        signal,
        quality,
        alignment,
        variants,
    })?;
    if warning_total > 0 {
        logger.warn(
            module_path!(),
            line!(),
            format_args!(
                concat!(
                    "event=warning_summary total={} unresolved_primary_calls={} ",
                    "multi_channel_unresolved_calls={} vendor_disagreements={} ",
                    "excluded_variant_candidates={} reference_origin_wrap={}"
                ),
                warning_total,
                read_warnings.unresolved_primary_calls,
                read_warnings.multi_channel_unresolved_calls,
                read_warnings.vendor_disagreements,
                excluded_variant_candidates,
                reference_origin_wrap
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
            warning_total,
            output.display().to_string(),
            bytes.len()
        ),
    )?;
    logger.sync()?;
    report::publish(&output, &bytes)
}
