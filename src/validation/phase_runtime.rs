//! Validation-only serialization of production read-local phase evidence.

use std::fs::{self, File};
use std::path::{Path, PathBuf};

use serde::Serialize;

use crate::checksum;
use crate::error::{Error, Result};
use crate::model::phase::{
    PhaseApplicability, PhaseEvidenceAvailability, PhaseInsufficiency, ReadPhaseEvidence,
};
use crate::model::read_observation::ReadObservation;
use crate::report;

const SCHEMA_VERSION: &str = "signal.validation_phase_runtime/v1";
const SOURCE_METHOD: &str = "signal.polyc_phase/v1";
const INDEX_FILE: &str = "index.json";
const WINDOWS_FILE: &str = "windows.csv";
const CANDIDATES_FILE: &str = "candidates.csv";

const WINDOWS_HEADER: &str = concat!(
    "read_sha256,tract_id,start_distance_after_tract,end_distance_after_tract,",
    "start_call_index_0based,end_call_index_0based,profile_observations,",
    "mean_profile_impurity,mean_zero_reference_mass\n"
);
const CANDIDATES_HEADER: &str = concat!(
    "read_sha256,tract_id,start_distance_after_tract,end_distance_after_tract,",
    "reference_offset_in_read_order,informative_positions,mean_zero_reference_mass,",
    "mean_shifted_reference_mass,mean_residual_mass\n"
);

#[derive(Debug)]
struct PhaseRuntimeArtifact {
    index: Vec<u8>,
    windows: Vec<u8>,
    candidates: Vec<u8>,
}

#[derive(Debug, Serialize)]
struct PhaseRuntimeIndex {
    schema_version: &'static str,
    source_method: &'static str,
    signal_version: &'static str,
    sample_id: String,
    reference_sha256: String,
    configuration_sha256: String,
    read_count: usize,
    window_count: usize,
    candidate_count: usize,
    files: PhaseRuntimeFiles,
    reads: Vec<PhaseRuntimeRead>,
}

#[derive(Debug, Serialize)]
struct PhaseRuntimeFiles {
    windows: PhaseRuntimeFile,
    candidates: PhaseRuntimeFile,
}

#[derive(Debug, Serialize)]
struct PhaseRuntimeFile {
    path: &'static str,
    sha256: String,
    rows: usize,
}

#[derive(Debug, Serialize)]
struct PhaseRuntimeRead {
    read_sha256: String,
    applicability: &'static str,
    tracts: Vec<PhaseRuntimeTract>,
}

#[derive(Debug, Serialize)]
struct PhaseRuntimeTract {
    tract_id: &'static str,
    availability: &'static str,
    insufficiency: Option<&'static str>,
    interrupt_aligned_base: Option<char>,
    window_count: usize,
}

/// Serializes exactly the already-computed `ReadObservation.phase` evidence and publishes
/// it as a validation-only artifact. No phase geometry or candidate math is recomputed here.
pub(crate) fn publish(
    sample_id: &str,
    reference_sha256: &str,
    configuration_sha256: &str,
    reads: &[ReadObservation],
) -> Result<()> {
    let artifact = serialize(
        sample_id,
        reference_sha256,
        configuration_sha256,
        reads,
    )?;
    let output = output_path(sample_id);
    publish_artifact(&output, &artifact)
}

fn serialize(
    sample_id: &str,
    reference_sha256: &str,
    configuration_sha256: &str,
    reads: &[ReadObservation],
) -> Result<PhaseRuntimeArtifact> {
    let mut ordered_reads = reads.iter().collect::<Vec<_>>();
    ordered_reads.sort_by(|left, right| left.input_sha256.cmp(&right.input_sha256));

    for pair in ordered_reads.windows(2) {
        if pair[0].input_sha256 == pair[1].input_sha256 {
            return Err(Error::Sample(format!(
                "validation phase runtime contains duplicate read SHA-256 {}",
                pair[0].input_sha256
            )));
        }
    }

    let mut windows = String::from(WINDOWS_HEADER);
    let mut candidates = String::from(CANDIDATES_HEADER);
    let mut read_rows = Vec::with_capacity(ordered_reads.len());
    let mut window_count = 0_usize;
    let mut candidate_count = 0_usize;

    for read in ordered_reads {
        if read.reference_sha256 != reference_sha256 {
            return Err(Error::Sample(format!(
                "validation phase runtime reference mismatch for read {}",
                read.input_sha256
            )));
        }
        if read.configuration_sha256 != configuration_sha256 {
            return Err(Error::Sample(format!(
                "validation phase runtime configuration mismatch for read {}",
                read.input_sha256
            )));
        }

        let (read_row, read_windows, read_candidates) = append_read(
            &read.input_sha256,
            &read.phase,
            &mut windows,
            &mut candidates,
        );
        read_rows.push(read_row);
        window_count += read_windows;
        candidate_count += read_candidates;
    }

    let windows = windows.into_bytes();
    let candidates = candidates.into_bytes();
    let index = PhaseRuntimeIndex {
        schema_version: SCHEMA_VERSION,
        source_method: SOURCE_METHOD,
        signal_version: env!("CARGO_PKG_VERSION"),
        sample_id: sample_id.to_owned(),
        reference_sha256: reference_sha256.to_owned(),
        configuration_sha256: configuration_sha256.to_owned(),
        read_count: read_rows.len(),
        window_count,
        candidate_count,
        files: PhaseRuntimeFiles {
            windows: PhaseRuntimeFile {
                path: WINDOWS_FILE,
                sha256: checksum::hex_sha256(&windows),
                rows: window_count,
            },
            candidates: PhaseRuntimeFile {
                path: CANDIDATES_FILE,
                sha256: checksum::hex_sha256(&candidates),
                rows: candidate_count,
            },
        },
        reads: read_rows,
    };
    let mut index = serde_json::to_vec_pretty(&index)?;
    index.push(b'\n');

    Ok(PhaseRuntimeArtifact {
        index,
        windows,
        candidates,
    })
}

fn append_read(
    read_sha256: &str,
    evidence: &ReadPhaseEvidence,
    windows: &mut String,
    candidates: &mut String,
) -> (PhaseRuntimeRead, usize, usize) {
    let mut tract_rows = Vec::with_capacity(evidence.tracts.len());
    let mut window_count = 0_usize;
    let mut candidate_count = 0_usize;

    for tract in &evidence.tracts {
        let (availability, insufficiency) = availability_labels(tract.availability);
        tract_rows.push(PhaseRuntimeTract {
            tract_id: tract.tract.label(),
            availability,
            insufficiency,
            interrupt_aligned_base: tract.interrupt_aligned_base,
            window_count: tract.windows.len(),
        });

        for window in &tract.windows {
            windows.push_str(&format!(
                "{read_sha256},{},{},{},{},{},{},{},{}\n",
                tract.tract.label(),
                window.start_distance_after_tract,
                window.end_distance_after_tract,
                window.start_call_index_0based,
                window.end_call_index_0based,
                window.profile_observations,
                window.mean_profile_impurity,
                window.mean_zero_reference_mass,
            ));
            window_count += 1;

            for candidate in &window.candidates {
                candidates.push_str(&format!(
                    "{read_sha256},{},{},{},{},{},{},{},{}\n",
                    tract.tract.label(),
                    window.start_distance_after_tract,
                    window.end_distance_after_tract,
                    candidate.reference_offset_in_read_order,
                    candidate.informative_positions,
                    csv_float(candidate.mean_zero_reference_mass),
                    csv_float(candidate.mean_shifted_reference_mass),
                    csv_float(candidate.mean_residual_mass),
                ));
                candidate_count += 1;
            }
        }
    }

    (
        PhaseRuntimeRead {
            read_sha256: read_sha256.to_owned(),
            applicability: applicability_label(evidence.applicability),
            tracts: tract_rows,
        },
        window_count,
        candidate_count,
    )
}

const fn applicability_label(applicability: PhaseApplicability) -> &'static str {
    match applicability {
        PhaseApplicability::NotApplicable => "not_applicable",
        PhaseApplicability::Applicable => "applicable",
    }
}

const fn availability_labels(
    availability: PhaseEvidenceAvailability,
) -> (&'static str, Option<&'static str>) {
    match availability {
        PhaseEvidenceAvailability::Measured => ("measured", None),
        PhaseEvidenceAvailability::Insufficient(reason) => {
            ("insufficient", Some(insufficiency_label(reason)))
        }
    }
}

const fn insufficiency_label(reason: PhaseInsufficiency) -> &'static str {
    match reason {
        PhaseInsufficiency::NoTractCoverage => "no_tract_coverage",
        PhaseInsufficiency::IncompleteTractCoverage => "incomplete_tract_coverage",
        PhaseInsufficiency::NoCallBackedTractSpan => "no_call_backed_tract_span",
        PhaseInsufficiency::NoCompleteProfileWindow => "no_complete_profile_window",
    }
}

fn csv_float(value: Option<f64>) -> String {
    value.map(|value| value.to_string()).unwrap_or_default()
}

pub(crate) fn output_path(sample_id: &str) -> PathBuf {
    PathBuf::from("validation-results").join(format!("{sample_id}.phase-runtime"))
}

fn publish_artifact(output: &Path, artifact: &PhaseRuntimeArtifact) -> Result<()> {
    if output.exists() {
        return Err(Error::Path {
            kind: "output",
            path: output.to_path_buf(),
            reason: "target already exists".into(),
        });
    }
    let parent = output
        .parent()
        .filter(|value| !value.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    fs::create_dir_all(parent).map_err(|source| Error::Output {
        path: parent.to_path_buf(),
        source,
    })?;
    fs::create_dir(output).map_err(|source| Error::Output {
        path: output.to_path_buf(),
        source,
    })?;

    let result = (|| {
        report::publish(&output.join(WINDOWS_FILE), &artifact.windows)?;
        report::publish(&output.join(CANDIDATES_FILE), &artifact.candidates)?;
        report::publish(&output.join(INDEX_FILE), &artifact.index)?;
        File::open(output)
            .and_then(|directory| directory.sync_all())
            .map_err(|source| Error::Output {
                path: output.to_path_buf(),
                source,
            })?;
        File::open(parent)
            .and_then(|directory| directory.sync_all())
            .map_err(|source| Error::Output {
                path: parent.to_path_buf(),
                source,
            })
    })();

    if let Err(error) = result {
        let _ = fs::remove_dir_all(output);
        return Err(error);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::phase::{
        PhaseCandidateEvidence, PhaseTractEvidence, PhaseTractId, PhaseWindowEvidence,
    };

    #[test]
    fn serializes_runtime_rows_without_recomputing_phase_geometry() {
        let evidence = ReadPhaseEvidence {
            applicability: PhaseApplicability::Applicable,
            tracts: vec![PhaseTractEvidence {
                tract: PhaseTractId::Hv2,
                availability: PhaseEvidenceAvailability::Measured,
                interrupt_aligned_base: Some('T'),
                windows: vec![PhaseWindowEvidence {
                    start_distance_after_tract: 2,
                    end_distance_after_tract: 31,
                    start_call_index_0based: 10,
                    end_call_index_0based: 34,
                    profile_observations: 25,
                    mean_profile_impurity: 0.125,
                    mean_zero_reference_mass: 0.75,
                    candidates: vec![
                        PhaseCandidateEvidence {
                            reference_offset_in_read_order: -1,
                            informative_positions: 4,
                            mean_zero_reference_mass: Some(0.6),
                            mean_shifted_reference_mass: Some(0.3),
                            mean_residual_mass: Some(0.1),
                        },
                        PhaseCandidateEvidence {
                            reference_offset_in_read_order: 1,
                            informative_positions: 0,
                            mean_zero_reference_mass: None,
                            mean_shifted_reference_mass: None,
                            mean_residual_mass: None,
                        },
                    ],
                }],
            }],
        };
        let mut windows = String::from(WINDOWS_HEADER);
        let mut candidates = String::from(CANDIDATES_HEADER);

        let (read, window_count, candidate_count) =
            append_read("abc", &evidence, &mut windows, &mut candidates);

        assert_eq!(read.applicability, "applicable");
        assert_eq!(read.tracts.len(), 1);
        assert_eq!(read.tracts[0].tract_id, "HV2_C");
        assert_eq!(read.tracts[0].availability, "measured");
        assert_eq!(window_count, 1);
        assert_eq!(candidate_count, 2);
        assert!(windows.contains("abc,HV2_C,2,31,10,34,25,0.125,0.75"));
        assert!(candidates.contains("abc,HV2_C,2,31,-1,4,0.6,0.3,0.1"));
        assert!(candidates.contains("abc,HV2_C,2,31,1,0,,,"));
    }
}
