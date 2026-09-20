//! Local per-locus measurement export for validation and threshold research.

use std::path::PathBuf;
use std::time::Instant;

use serde::Serialize;

use crate::cli::SampleArgs;
use crate::error::{Error, Result};
use crate::logger::Logger;
use crate::model::alignment::Orientation;
use crate::model::basecalls::PeakSource;
use crate::model::locus_evidence::EvidenceProfile;
use crate::model::phase::{PhaseApplicability, PhaseEvidenceAvailability};
use crate::model::read_observation::ReadObservation;
use crate::model::sample_evidence::{
    LocusState, NucleotideContribution, ProfileHeterogeneity, SampleLocusEvidence,
    SampleLocusObservation,
};
use crate::report;
use crate::sample as sample_science;
use crate::validation::{ValidationExportRequest, phase_runtime};

use super::{input, sample_reads};

const SCHEMA_VERSION: &str = "signal.validation_locus/v2";

#[derive(Serialize)]
struct ValidationLocusRow<'a> {
    schema_version: &'static str,
    signal_version: &'static str,
    sample_id: &'a str,
    reference_sha256: &'a str,
    configuration_sha256: &'a str,
    position_1based: usize,
    reference_base: char,

    reads: usize,
    forward_reads: usize,
    reverse_reads: usize,
    reference_reads: usize,
    alternate_reads: usize,
    unresolved_reads: usize,
    deletion_reads: usize,
    profile_reads: usize,
    profile_forward_reads: usize,
    profile_reverse_reads: usize,

    contributors: usize,
    forward_contributors: usize,
    reverse_contributors: usize,

    mean_a: Option<f64>,
    mean_c: Option<f64>,
    mean_g: Option<f64>,
    mean_t: Option<f64>,

    within_profile_impurity: Option<f64>,
    between_profile_dispersion: Option<f64>,
    total_profile_heterogeneity: Option<f64>,

    forward_within_profile_impurity: Option<f64>,
    forward_between_profile_dispersion: Option<f64>,
    forward_total_profile_heterogeneity: Option<f64>,

    reverse_within_profile_impurity: Option<f64>,
    reverse_between_profile_dispersion: Option<f64>,
    reverse_total_profile_heterogeneity: Option<f64>,

    directional_profile_distance: Option<f64>,

    noisy_observations: usize,
    missing_profile_observations: usize,
    deletion_observations: usize,
    observations: Vec<ValidationObservationRow<'a>>,
}

#[derive(Serialize)]
struct ValidationObservationRow<'a> {
    read_sha256: &'a str,
    orientation: Orientation,
    state: LocusState,
    aligned_base: Option<char>,
    quality: Option<u8>,
    call_index_0based: Option<usize>,

    source_primary: Option<char>,
    source_ambiguity: Option<char>,
    ploc_0based: Option<usize>,
    window_start_0based: Option<usize>,
    window_end_0based_exclusive: Option<usize>,

    primary_peak_position_0based: Option<usize>,
    primary_peak_offset_from_ploc: Option<i64>,
    event_position_0based: Option<usize>,
    event_offset_from_ploc: Option<i64>,
    event_offset_from_primary_peak: Option<i64>,

    channel_peak_positions_acgt_reference: Option<[usize; 4]>,
    channel_peak_heights_acgt_reference: Option<[i32; 4]>,
    channel_peak_sources_acgt_reference: Option<[PeakSource; 4]>,
    primary_peak_heights_acgt_reference: Option<[i32; 4]>,

    corrected_amplitudes_acgt_reference: Option<[f64; 4]>,
    snrs_acgt_reference: Option<[f64; 4]>,
    profile_acgt_reference: Option<[f64; 4]>,
    in_noisy_region: Option<bool>,
}

pub(crate) fn run(request: &ValidationExportRequest) -> Result<()> {
    input::validate_sample_id(&request.sample_id)?;
    let mut logger = Logger::open(&format!("{}.validation", request.sample_id))?;
    let started = Instant::now();
    logger.info(
        module_path!(),
        line!(),
        format_args!(
            "event=validation_export_started version={} sample_id={:?} traces={} reference_path={:?}",
            env!("CARGO_PKG_VERSION"),
            request.sample_id,
            request.traces.len(),
            request.reference.display().to_string()
        ),
    )?;

    let mut stage = "input_loading";
    match run_logged(request, &mut logger, &mut stage, started) {
        Ok(()) => Ok(()),
        Err(error) => Err(super::record_failure(
            &mut logger,
            "validation_export_failed",
            stage,
            started,
            error,
        )),
    }
}

fn run_logged(
    request: &ValidationExportRequest,
    logger: &mut Logger,
    stage: &mut &'static str,
    started: Instant,
) -> Result<()> {
    let args = SampleArgs {
        sample_id: request.sample_id.clone(),
        traces: request.traces.clone(),
        reference: request.reference.clone(),
    };

    *stage = "input_loading";
    let inputs = input::load_sample(&args)?;

    *stage = "read_processing";
    let completed_reads = sample_reads::build(
        &inputs.traces,
        &inputs.reference,
        &inputs.config,
        logger,
        stage,
    )?;
    let reads = completed_reads.reads;
    let applicable_phase_reads = reads
        .iter()
        .filter(|read| read.phase.applicability == PhaseApplicability::Applicable)
        .count();
    let measured_phase_tracts = reads
        .iter()
        .flat_map(|read| &read.phase.tracts)
        .filter(|tract| tract.availability == PhaseEvidenceAvailability::Measured)
        .count();
    let insufficient_phase_tracts = reads
        .iter()
        .flat_map(|read| &read.phase.tracts)
        .filter(|tract| {
            matches!(
                tract.availability,
                PhaseEvidenceAvailability::Insufficient(_)
            )
        })
        .count();
    let phase_windows = reads
        .iter()
        .flat_map(|read| &read.phase.tracts)
        .map(|tract| tract.windows.len())
        .sum::<usize>();
    logger.info(
        module_path!(),
        line!(),
        format_args!(
            concat!(
                "event=validation_phase_evidence_summary reads={} applicable_reads={} ",
                "measured_tracts={} insufficient_tracts={} windows={}"
            ),
            reads.len(),
            applicable_phase_reads,
            measured_phase_tracts,
            insufficient_phase_tracts,
            phase_windows
        ),
    )?;

    *stage = "sample_aggregation";
    let evidence = sample_science::aggregate(&reads, &inputs.config.sample_reconciliation)?;
    let covered = sample_science::all_covered_loci(&reads)?;

    *stage = "validation_serialization";
    let bytes = serialize_rows(
        &request.sample_id,
        &evidence.reference_sha256,
        &evidence.configuration_sha256,
        &covered.reads,
        &covered.loci,
    )?;
    let output = output_path(&request.sample_id);
    let phase_output = phase_runtime::output_path(&request.sample_id);
    if phase_output.exists() {
        return Err(Error::Path {
            kind: "output",
            path: phase_output,
            reason: "target already exists".into(),
        });
    }

    logger.info(
        module_path!(),
        line!(),
        format_args!(
            concat!(
                "event=validation_export_ready total_elapsed_ms={} sample_id={:?} ",
                "covered_loci={} differential_loci={} output_path={:?} bytes={}"
            ),
            started.elapsed().as_millis(),
            request.sample_id,
            covered.loci.len(),
            evidence.locus_differences.len(),
            output.display().to_string(),
            bytes.len()
        ),
    )?;
    logger.sync()?;

    *stage = "validation_publication";
    report::publish(&output, &bytes)?;
    phase_runtime::publish(
        &request.sample_id,
        &evidence.reference_sha256,
        &evidence.configuration_sha256,
        &reads,
    )?;
    Ok(())
}

fn output_path(sample_id: &str) -> PathBuf {
    PathBuf::from("validation-results").join(format!("{sample_id}.jsonl"))
}

fn serialize_rows(
    sample_id: &str,
    reference_sha256: &str,
    configuration_sha256: &str,
    reads: &[&ReadObservation],
    loci: &[SampleLocusEvidence],
) -> Result<Vec<u8>> {
    let mut bytes = Vec::new();
    for locus in loci {
        let row = row(
            sample_id,
            reference_sha256,
            configuration_sha256,
            reads,
            locus,
        )?;
        serde_json::to_writer(&mut bytes, &row)?;
        bytes.push(b'\n');
    }
    Ok(bytes)
}

fn row<'a>(
    sample_id: &'a str,
    reference_sha256: &'a str,
    configuration_sha256: &'a str,
    reads: &'a [&'a ReadObservation],
    locus: &'a SampleLocusEvidence,
) -> Result<ValidationLocusRow<'a>> {
    let topology = locus.support_topology;
    let support = locus.nucleotide_support;
    let mean = profile_channels(support.mean_profile);
    let geometry = geometry_channels(support.heterogeneity);
    let forward_geometry = geometry_channels(support.forward_heterogeneity);
    let reverse_geometry = geometry_channels(support.reverse_heterogeneity);

    let observations = locus
        .observations
        .iter()
        .map(|observation| observation_row(observation, reads))
        .collect::<Result<Vec<_>>>()?;

    Ok(ValidationLocusRow {
        schema_version: SCHEMA_VERSION,
        signal_version: env!("CARGO_PKG_VERSION"),
        sample_id,
        reference_sha256,
        configuration_sha256,
        position_1based: locus.position_1based,
        reference_base: locus.reference_base,

        reads: topology.reads,
        forward_reads: topology.forward_reads,
        reverse_reads: topology.reverse_reads,
        reference_reads: topology.reference_reads,
        alternate_reads: topology.alternate_reads,
        unresolved_reads: topology.unresolved_reads,
        deletion_reads: topology.deletion_reads,
        profile_reads: topology.profile_reads,
        profile_forward_reads: topology.profile_forward_reads,
        profile_reverse_reads: topology.profile_reverse_reads,

        contributors: support.contributors,
        forward_contributors: support.forward_contributors,
        reverse_contributors: support.reverse_contributors,

        mean_a: mean[0],
        mean_c: mean[1],
        mean_g: mean[2],
        mean_t: mean[3],

        within_profile_impurity: geometry[0],
        between_profile_dispersion: geometry[1],
        total_profile_heterogeneity: geometry[2],

        forward_within_profile_impurity: forward_geometry[0],
        forward_between_profile_dispersion: forward_geometry[1],
        forward_total_profile_heterogeneity: forward_geometry[2],

        reverse_within_profile_impurity: reverse_geometry[0],
        reverse_between_profile_dispersion: reverse_geometry[1],
        reverse_total_profile_heterogeneity: reverse_geometry[2],

        directional_profile_distance: support.directional_profile_distance,

        noisy_observations: locus
            .observations
            .iter()
            .filter(|observation| {
                observation
                    .signal
                    .is_some_and(|signal| signal.in_noisy_region)
            })
            .count(),
        missing_profile_observations: locus
            .observations
            .iter()
            .filter(|observation| {
                observation.nucleotide_contribution == NucleotideContribution::MissingProfile
            })
            .count(),
        deletion_observations: locus
            .observations
            .iter()
            .filter(|observation| {
                observation.nucleotide_contribution == NucleotideContribution::DeletionEvent
            })
            .count(),
        observations,
    })
}

fn observation_row<'a>(
    observation: &'a SampleLocusObservation,
    reads: &'a [&'a ReadObservation],
) -> Result<ValidationObservationRow<'a>> {
    let read = reads.get(observation.read_index).ok_or_else(|| {
        Error::Sample(format!(
            "validation locus observation references missing read {}",
            observation.read_index
        ))
    })?;

    let Some(call_index_0based) = observation.call_index_0based else {
        return Ok(ValidationObservationRow {
            read_sha256: &read.input_sha256,
            orientation: read.alignment.orientation,
            state: observation.state,
            aligned_base: observation.base,
            quality: observation.quality,
            call_index_0based: None,
            source_primary: None,
            source_ambiguity: None,
            ploc_0based: None,
            window_start_0based: None,
            window_end_0based_exclusive: None,
            primary_peak_position_0based: None,
            primary_peak_offset_from_ploc: None,
            event_position_0based: None,
            event_offset_from_ploc: None,
            event_offset_from_primary_peak: None,
            channel_peak_positions_acgt_reference: None,
            channel_peak_heights_acgt_reference: None,
            channel_peak_sources_acgt_reference: None,
            primary_peak_heights_acgt_reference: None,
            corrected_amplitudes_acgt_reference: None,
            snrs_acgt_reference: None,
            profile_acgt_reference: None,
            in_noisy_region: None,
        });
    };

    let call = read
        .calls
        .calls
        .get(call_index_0based)
        .filter(|call| call.index_0based == call_index_0based)
        .ok_or_else(|| {
            Error::Sample(format!(
                "validation call index {call_index_0based} is inconsistent"
            ))
        })?;
    let locus = read
        .signal
        .loci
        .get(call_index_0based)
        .filter(|locus| locus.call_index_0based == call_index_0based)
        .ok_or_else(|| {
            Error::Sample(format!(
                "validation signal locus {call_index_0based} is inconsistent"
            ))
        })?;
    let orientation = read.alignment.orientation;
    let primary_peak_position = call
        .primary_peak_evidence
        .as_ref()
        .map(|evidence| evidence.position_0based);
    let primary_peak_heights = call
        .primary_peak_evidence
        .as_ref()
        .map(|evidence| orientation.reference_peak_heights(evidence.channel_heights));
    let signal = observation.signal.ok_or_else(|| {
        Error::Sample(format!(
            "call-backed validation observation {call_index_0based} lacks signal evidence"
        ))
    })?;

    Ok(ValidationObservationRow {
        read_sha256: &read.input_sha256,
        orientation,
        state: observation.state,
        aligned_base: observation.base,
        quality: observation.quality,
        call_index_0based: Some(call_index_0based),
        source_primary: Some(call.primary),
        source_ambiguity: Some(call.ambiguity),
        ploc_0based: Some(call.ploc_0based),
        window_start_0based: Some(call.window_start_0based),
        window_end_0based_exclusive: Some(call.window_end_0based_exclusive),
        primary_peak_position_0based: primary_peak_position,
        primary_peak_offset_from_ploc: primary_peak_position
            .map(|position| signed_offset(position, call.ploc_0based))
            .transpose()?,
        event_position_0based: Some(locus.event_position_0based),
        event_offset_from_ploc: Some(signed_offset(
            locus.event_position_0based,
            call.ploc_0based,
        )?),
        event_offset_from_primary_peak: primary_peak_position
            .map(|position| signed_offset(locus.event_position_0based, position))
            .transpose()?,
        channel_peak_positions_acgt_reference: Some(reference_usize_values(
            orientation,
            call.peaks.map(|peak| peak.position_0based),
        )),
        channel_peak_heights_acgt_reference: Some(
            orientation.reference_peak_heights(call.peaks.map(|peak| peak.height)),
        ),
        channel_peak_sources_acgt_reference: Some(reference_peak_sources(
            orientation,
            call.peaks.map(|peak| peak.source),
        )),
        primary_peak_heights_acgt_reference: primary_peak_heights,
        corrected_amplitudes_acgt_reference: Some(signal.corrected_amplitudes),
        snrs_acgt_reference: Some(signal.snrs),
        profile_acgt_reference: signal.profile.map(|profile| profile.weights),
        in_noisy_region: Some(signal.in_noisy_region),
    })
}

fn signed_offset(position: usize, anchor: usize) -> Result<i64> {
    let magnitude = i64::try_from(position.abs_diff(anchor))
        .map_err(|_| Error::Sample("validation sample-coordinate offset exceeds i64".into()))?;
    Ok(if position >= anchor {
        magnitude
    } else {
        -magnitude
    })
}

const fn reference_usize_values(orientation: Orientation, values: [usize; 4]) -> [usize; 4] {
    match orientation {
        Orientation::Forward => values,
        Orientation::Reverse => [values[3], values[2], values[1], values[0]],
    }
}

const fn reference_peak_sources(
    orientation: Orientation,
    values: [PeakSource; 4],
) -> [PeakSource; 4] {
    match orientation {
        Orientation::Forward => values,
        Orientation::Reverse => [values[3], values[2], values[1], values[0]],
    }
}

fn profile_channels(profile: Option<EvidenceProfile>) -> [Option<f64>; 4] {
    profile.map_or([None; 4], |profile| profile.weights.map(Some))
}

fn geometry_channels(geometry: Option<ProfileHeterogeneity>) -> [Option<f64>; 3] {
    geometry.map_or([None; 3], |geometry| {
        [
            Some(geometry.within_profile_impurity),
            Some(geometry.between_profile_dispersion),
            Some(geometry.total_profile_heterogeneity),
        ]
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn absent_profile_and_geometry_serialize_as_null_channels() {
        assert_eq!(profile_channels(None), [None; 4]);
        assert_eq!(geometry_channels(None), [None; 3]);
    }

    #[test]
    fn diagnostic_channel_projection_and_offsets_are_reference_oriented() -> Result<()> {
        assert_eq!(
            reference_usize_values(Orientation::Reverse, [1, 2, 3, 4]),
            [4, 3, 2, 1]
        );
        assert_eq!(
            reference_peak_sources(
                Orientation::Reverse,
                [
                    PeakSource::LocalMaximum,
                    PeakSource::PlocFallback,
                    PeakSource::LocalMaximum,
                    PeakSource::PlocFallback,
                ],
            ),
            [
                PeakSource::PlocFallback,
                PeakSource::LocalMaximum,
                PeakSource::PlocFallback,
                PeakSource::LocalMaximum,
            ]
        );
        assert_eq!(signed_offset(12, 10)?, 2);
        assert_eq!(signed_offset(8, 10)?, -2);
        assert_eq!(signed_offset(10, 10)?, 0);
        Ok(())
    }

    #[test]
    fn profile_and_geometry_channels_preserve_values() {
        let profile = EvidenceProfile {
            weights: [0.1, 0.2, 0.3, 0.4],
        };
        assert_eq!(
            profile_channels(Some(profile)),
            [Some(0.1), Some(0.2), Some(0.3), Some(0.4)]
        );

        let geometry = ProfileHeterogeneity {
            within_profile_impurity: 0.2,
            between_profile_dispersion: 0.1,
            total_profile_heterogeneity: 0.3,
        };
        assert_eq!(
            geometry_channels(Some(geometry)),
            [Some(0.2), Some(0.1), Some(0.3)]
        );
    }
}
