//! Local per-locus measurement export for validation and threshold research.

use std::path::PathBuf;
use std::time::Instant;

use serde::Serialize;

use crate::cli::SampleArgs;
use crate::error::Result;
use crate::logger::Logger;
use crate::model::locus_evidence::EvidenceProfile;
use crate::model::sample_evidence::{
    LocusNucleotideSupport, NucleotideContribution, ProfileHeterogeneity, SampleLocusEvidence,
};
use crate::report;
use crate::sample as sample_science;
use crate::validation::ValidationExportRequest;

use super::{input, sample_reads};

const SCHEMA_VERSION: &str = "signal.validation_locus/v1";

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

    *stage = "sample_aggregation";
    let evidence = sample_science::aggregate(&reads, &inputs.config.sample_reconciliation)?;
    let loci = sample_science::all_covered_loci(&reads)?;

    *stage = "validation_serialization";
    let bytes = serialize_rows(
        &request.sample_id,
        &evidence.reference_sha256,
        &evidence.configuration_sha256,
        &loci,
    )?;
    let output = output_path(&request.sample_id);

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
            loci.len(),
            evidence.locus_differences.len(),
            output.display().to_string(),
            bytes.len()
        ),
    )?;
    logger.sync()?;

    *stage = "validation_publication";
    report::publish(&output, &bytes)
}

fn output_path(sample_id: &str) -> PathBuf {
    PathBuf::from("validation-results").join(format!("{sample_id}.jsonl"))
}

fn serialize_rows(
    sample_id: &str,
    reference_sha256: &str,
    configuration_sha256: &str,
    loci: &[SampleLocusEvidence],
) -> Result<Vec<u8>> {
    let mut bytes = Vec::new();
    for locus in loci {
        let row = row(
            sample_id,
            reference_sha256,
            configuration_sha256,
            locus,
        );
        serde_json::to_writer(&mut bytes, &row)?;
        bytes.push(b'\n');
    }
    Ok(bytes)
}

fn row<'a>(
    sample_id: &'a str,
    reference_sha256: &'a str,
    configuration_sha256: &'a str,
    locus: &'a SampleLocusEvidence,
) -> ValidationLocusRow<'a> {
    let topology = locus.support_topology;
    let support = locus.nucleotide_support;
    let mean = profile_channels(support.mean_profile);
    let geometry = geometry_channels(support.heterogeneity);
    let forward_geometry = geometry_channels(support.forward_heterogeneity);
    let reverse_geometry = geometry_channels(support.reverse_heterogeneity);

    ValidationLocusRow {
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
