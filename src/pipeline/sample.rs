//! Multi-read sample evidence orchestration and publication.

use std::time::Instant;

use crate::cli::SampleArgs;
use crate::error::Result;
use crate::logger::Logger;
use crate::pipeline::{input, observation};
use crate::report::{self, CompletedSampleEvidence};
use crate::sample as sample_science;

/// Runs one sample-evidence operation with one sample-level append-only log.
pub(crate) fn run(args: &SampleArgs) -> Result<()> {
    input::validate_sample_id(&args.sample_id)?;
    let mut logger = Logger::open(&args.sample_id)?;
    let started = Instant::now();
    logger.info(
        module_path!(),
        line!(),
        format_args!(
            "event=sample_started version={} sample_id={:?} traces={} reference_path={:?}",
            env!("CARGO_PKG_VERSION"),
            args.sample_id,
            args.traces.len(),
            args.reference.display().to_string()
        ),
    )?;

    let mut stage = "input_loading";
    match run_logged(args, &mut logger, &mut stage, started) {
        Ok(()) => Ok(()),
        Err(error) => Err(super::record_failure(
            &mut logger,
            "sample_failed",
            stage,
            started,
            error,
        )),
    }
}

fn run_logged(
    args: &SampleArgs,
    logger: &mut Logger,
    stage: &mut &'static str,
    started: Instant,
) -> Result<()> {
    *stage = "input_loading";
    let stage_started = Instant::now();
    let inputs = input::load_sample(args)?;
    logger.info(
        module_path!(),
        line!(),
        format_args!(
            concat!(
                "event=sample_inputs_loaded elapsed_ms={} sample_id={:?} traces={} ",
                "reference_name={:?} reference_sha256={} topology={:?} reference_bases={} ",
                "config_path={:?} config_sha256={} output_path={:?}"
            ),
            stage_started.elapsed().as_millis(),
            args.sample_id,
            inputs.traces.len(),
            inputs.reference.name,
            inputs.reference.sequence_sha256,
            inputs.reference.topology,
            inputs.reference.len(),
            inputs.config.source_path.display().to_string(),
            inputs.config.source_sha256,
            inputs.output.display().to_string()
        ),
    )?;

    let mut reads = Vec::with_capacity(inputs.traces.len());
    let mut warning_total = 0usize;
    for (index, trace) in inputs.traces.iter().enumerate() {
        logger.info(
            module_path!(),
            line!(),
            format_args!(
                "event=sample_read_started read_index={} trace_name={:?} trace_sha256={}",
                index, trace.source_name, trace.source_sha256
            ),
        )?;
        let completed =
            observation::build(trace, &inputs.reference, &inputs.config, logger, stage)?;
        warning_total += completed.warning_total;
        logger.info(
            module_path!(),
            line!(),
            format_args!(
                "event=sample_read_completed read_index={} trace_sha256={} orientation={:?} segments={} variants={}",
                index,
                completed.read.input_sha256,
                completed.read.alignment.orientation,
                completed.read.alignment.reference_segments.len(),
                completed.read.variants.reported.len()
            ),
        )?;
        reads.push(completed.read);
    }

    *stage = "sample_aggregation";
    let stage_started = Instant::now();
    let evidence = sample_science::aggregate(&reads, &inputs.config.sample_reconciliation)?;
    let profiled_locus_observations = evidence
        .locus_differences
        .iter()
        .map(|difference| difference.support_topology.profile_reads)
        .sum::<usize>();
    let profiled_locus_forward_reads = evidence
        .locus_differences
        .iter()
        .map(|difference| difference.support_topology.profile_forward_reads)
        .sum::<usize>();
    let profiled_locus_reverse_reads = evidence
        .locus_differences
        .iter()
        .map(|difference| difference.support_topology.profile_reverse_reads)
        .sum::<usize>();
    let profiled_variant_calls = evidence
        .variants
        .iter()
        .flat_map(|variant| &variant.support)
        .flat_map(|support| &support.calls)
        .filter(|call| call.signal.profile.is_some())
        .count();
    let noisy_locus_observations = evidence
        .locus_differences
        .iter()
        .flat_map(|difference| &difference.observations)
        .filter(|observation| {
            observation
                .signal
                .as_ref()
                .is_some_and(|signal| signal.in_noisy_region)
        })
        .count();
    let noisy_variant_calls = evidence
        .variants
        .iter()
        .flat_map(|variant| &variant.support)
        .flat_map(|support| &support.calls)
        .filter(|call| call.signal.in_noisy_region)
        .count();
    let eligible_nucleotide_locus_observations = evidence
        .locus_differences
        .iter()
        .flat_map(|difference| &difference.observations)
        .filter(|observation| {
            observation.nucleotide_contribution
                == crate::model::sample_evidence::NucleotideContribution::Eligible
        })
        .count();
    let missing_profile_locus_observations = evidence
        .locus_differences
        .iter()
        .flat_map(|difference| &difference.observations)
        .filter(|observation| {
            observation.nucleotide_contribution
                == crate::model::sample_evidence::NucleotideContribution::MissingProfile
        })
        .count();
    let deletion_event_locus_observations = evidence
        .locus_differences
        .iter()
        .flat_map(|difference| &difference.observations)
        .filter(|observation| {
            observation.nucleotide_contribution
                == crate::model::sample_evidence::NucleotideContribution::DeletionEvent
        })
        .count();
    let nucleotide_support_loci = evidence
        .locus_differences
        .iter()
        .filter(|difference| difference.nucleotide_support.mean_profile.is_some())
        .count();
    let bidirectional_nucleotide_support_loci = evidence
        .locus_differences
        .iter()
        .filter(|difference| {
            difference.nucleotide_support.forward_mean_profile.is_some()
                && difference.nucleotide_support.reverse_mean_profile.is_some()
        })
        .count();
    let unweighted_nucleotide_profile_mass = evidence
        .locus_differences
        .iter()
        .flat_map(|difference| difference.nucleotide_support.support)
        .sum::<f64>();
    let locus_positive_corrected_channels = evidence
        .locus_differences
        .iter()
        .flat_map(|difference| &difference.observations)
        .filter_map(|observation| observation.signal.as_ref())
        .flat_map(|signal| signal.corrected_amplitudes)
        .filter(|value| *value > 0.0)
        .count();
    let locus_positive_snr_channels = evidence
        .locus_differences
        .iter()
        .flat_map(|difference| &difference.observations)
        .filter_map(|observation| observation.signal.as_ref())
        .flat_map(|signal| signal.snrs)
        .filter(|value| *value > 0.0)
        .count();
    let variant_positive_corrected_channels = evidence
        .variants
        .iter()
        .flat_map(|variant| &variant.support)
        .flat_map(|support| &support.calls)
        .flat_map(|call| call.signal.corrected_amplitudes)
        .filter(|value| *value > 0.0)
        .count();
    let variant_positive_snr_channels = evidence
        .variants
        .iter()
        .flat_map(|variant| &variant.support)
        .flat_map(|support| &support.calls)
        .flat_map(|call| call.signal.snrs)
        .filter(|value| *value > 0.0)
        .count();
    let locus_forward_reads = evidence
        .locus_differences
        .iter()
        .map(|difference| difference.support_topology.forward_reads)
        .sum::<usize>();
    let locus_reverse_reads = evidence
        .locus_differences
        .iter()
        .map(|difference| difference.support_topology.reverse_reads)
        .sum::<usize>();
    let locus_reference_reads = evidence
        .locus_differences
        .iter()
        .map(|difference| difference.support_topology.reference_reads)
        .sum::<usize>();
    let locus_alternate_reads = evidence
        .locus_differences
        .iter()
        .map(|difference| difference.support_topology.alternate_reads)
        .sum::<usize>();
    let locus_unresolved_reads = evidence
        .locus_differences
        .iter()
        .map(|difference| difference.support_topology.unresolved_reads)
        .sum::<usize>();
    let locus_deletion_reads = evidence
        .locus_differences
        .iter()
        .map(|difference| difference.support_topology.deletion_reads)
        .sum::<usize>();
    logger.info(
        module_path!(),
        line!(),
        format_args!(
            concat!(
                "event=sample_aggregation_completed elapsed_ms={} reads={} coverage_segments={} ",
                "overlaps={} eligible_overlaps={} locus_differences={} profiled_locus_observations={} ",
                "profiled_locus_forward_reads={} profiled_locus_reverse_reads={} noisy_locus_observations={} ",
                "eligible_nucleotide_locus_observations={} missing_profile_locus_observations={} ",
                "deletion_event_locus_observations={} nucleotide_support_loci={} ",
                "bidirectional_nucleotide_support_loci={} unweighted_nucleotide_profile_mass={:.6} ",
                "locus_positive_corrected_channels={} locus_positive_snr_channels={} ",
                "locus_forward_reads={} locus_reverse_reads={} locus_reference_reads={} ",
                "locus_alternate_reads={} locus_unresolved_reads={} locus_deletion_reads={} variants={} ",
                "profiled_variant_calls={} noisy_variant_calls={} variant_positive_corrected_channels={} ",
                "variant_positive_snr_channels={}"
            ),
            stage_started.elapsed().as_millis(),
            evidence.reads.len(),
            evidence.coverage.len(),
            evidence.overlaps.len(),
            evidence
                .overlaps
                .iter()
                .filter(|overlap| overlap.eligible)
                .count(),
            evidence.locus_differences.len(),
            profiled_locus_observations,
            profiled_locus_forward_reads,
            profiled_locus_reverse_reads,
            noisy_locus_observations,
            eligible_nucleotide_locus_observations,
            missing_profile_locus_observations,
            deletion_event_locus_observations,
            nucleotide_support_loci,
            bidirectional_nucleotide_support_loci,
            unweighted_nucleotide_profile_mass,
            locus_positive_corrected_channels,
            locus_positive_snr_channels,
            locus_forward_reads,
            locus_reverse_reads,
            locus_reference_reads,
            locus_alternate_reads,
            locus_unresolved_reads,
            locus_deletion_reads,
            evidence.variants.len(),
            profiled_variant_calls,
            noisy_variant_calls,
            variant_positive_corrected_channels,
            variant_positive_snr_channels
        ),
    )?;

    *stage = "reporting";
    let stage_started = Instant::now();
    let output = inputs.output.clone();
    let result = report::build_sample(CompletedSampleEvidence {
        sample_id: args.sample_id.clone(),
        reference: inputs.reference,
        evidence,
    })?;
    let reads = result.reads.len();
    let coverage_segments = result.coverage.len();
    let overlaps = result.overlaps.len();
    let locus_differences = result.locus_differences.len();
    let variants = result.variants.len();
    let schema_version = result.schema_version;
    let bytes = report::serialize(&result)?;

    *stage = "result_publication";
    logger.info(
        module_path!(),
        line!(),
        format_args!(
            concat!(
                "event=sample_result_ready_for_publication elapsed_ms={} total_elapsed_ms={} ",
                "schema={} reads={} coverage_segments={} overlaps={} locus_differences={} variants={} ",
                "read_warnings={} output_path={:?} bytes={}"
            ),
            stage_started.elapsed().as_millis(),
            started.elapsed().as_millis(),
            schema_version,
            reads,
            coverage_segments,
            overlaps,
            locus_differences,
            variants,
            warning_total,
            output.display().to_string(),
            bytes.len()
        ),
    )?;
    logger.sync()?;
    report::publish(&output, &bytes)
}
