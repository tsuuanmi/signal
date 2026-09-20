mod support;

use std::fs;

use assert_cmd::Command;
use predicates::prelude::*;
use serde_json::Value;
use tempfile::tempdir;

use support::{write_abif, write_config, write_reference};

const QUERY: &str = "ACGTCAGTACGATCGTACCTGAGTACGA";
const SAMPLE_ID: &str = "validation-1";

#[test]
fn exports_all_covered_loci_without_production_result() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    let forward = directory.path().join("forward.ab1");
    let reverse = directory.path().join("reverse.ab1");

    write_reference(&reference, &format!("TTTT{QUERY}CCCC"))?;
    write_config(&config, "linear")?;
    write_abif(&forward, QUERY)?;
    write_abif(&reverse, &reverse_complement(QUERY))?;

    let mut command = Command::new(env!("CARGO_BIN_EXE_signal-validation"));
    command
        .current_dir(directory.path())
        .env("SIGNAL_CONFIG", &config)
        .arg(SAMPLE_ID)
        .arg(&forward)
        .arg(&reverse)
        .arg("--reference")
        .arg(&reference)
        .assert()
        .success()
        .stdout(predicate::str::is_empty())
        .stderr(predicate::str::is_empty());

    let output = directory
        .path()
        .join("validation-results")
        .join(format!("{SAMPLE_ID}.jsonl"));
    let text = fs::read_to_string(&output)?;
    let rows = text
        .lines()
        .map(serde_json::from_str::<Value>)
        .collect::<Result<Vec<_>, _>>()?;

    assert_eq!(rows.len(), QUERY.len());
    assert!(rows.iter().all(|row| {
        row["schema_version"] == "signal.validation_locus/v2"
            && row["sample_id"] == SAMPLE_ID
            && row["reads"] == 2
            && row["reference_reads"] == 2
            && row["alternate_reads"] == 0
            && row["deletion_reads"] == 0
    }));
    assert!(
        rows.iter()
            .all(|row| row["within_profile_impurity"].is_number())
    );
    assert!(
        rows.iter()
            .all(|row| row["directional_profile_distance"].is_number())
    );
    assert!(rows.iter().all(|row| {
        row["observations"].as_array().is_some_and(|observations| {
            observations.len() == 2
                && observations.iter().all(|observation| {
                    observation["call_index_0based"].is_number()
                        && observation["ploc_0based"].is_number()
                        && observation["primary_peak_position_0based"].is_number()
                        && observation["event_position_0based"].is_number()
                        && observation["event_offset_from_ploc"].is_number()
                        && observation["event_offset_from_primary_peak"].is_number()
                        && observation["channel_peak_positions_acgt_reference"]
                            .as_array()
                            .is_some_and(|values| values.len() == 4)
                        && observation["corrected_amplitudes_acgt_reference"]
                            .as_array()
                            .is_some_and(|values| values.len() == 4)
                        && observation["profile_acgt_reference"]
                            .as_array()
                            .is_some_and(|values| values.len() == 4)
                })
        })
    }));

    assert!(!directory.path().join("results").exists());
    assert!(
        directory
            .path()
            .join("logs")
            .join(format!("{SAMPLE_ID}.validation.log"))
            .is_file()
    );

    let phase_runtime = directory
        .path()
        .join("validation-results")
        .join(format!("{SAMPLE_ID}.phase-runtime"));
    let phase_index: Value =
        serde_json::from_str(&fs::read_to_string(phase_runtime.join("index.json"))?)?;
    assert_eq!(
        phase_index["schema_version"],
        "signal.validation_phase_runtime/v1"
    );
    assert_eq!(phase_index["source_method"], "signal.polyc_phase/v1");
    assert_eq!(phase_index["sample_id"], SAMPLE_ID);
    assert_eq!(phase_index["read_count"], 2);
    assert_eq!(phase_index["window_count"], 0);
    assert_eq!(phase_index["candidate_count"], 0);
    assert!(phase_index["reads"].as_array().is_some_and(|reads| {
        reads.len() == 2
            && reads
                .iter()
                .all(|read| read["applicability"] == "not_applicable")
    }));
    assert_eq!(
        fs::read_to_string(phase_runtime.join("windows.csv"))?,
        concat!(
            "read_sha256,tract_id,start_distance_after_tract,end_distance_after_tract,",
            "start_call_index_0based,end_call_index_0based,profile_observations,",
            "mean_profile_impurity,mean_zero_reference_mass\n"
        )
    );
    assert_eq!(
        fs::read_to_string(phase_runtime.join("candidates.csv"))?,
        concat!(
            "read_sha256,tract_id,start_distance_after_tract,end_distance_after_tract,",
            "reference_offset_in_read_order,informative_positions,mean_zero_reference_mass,",
            "mean_shifted_reference_mass,mean_residual_mass\n"
        )
    );

    Ok(())
}

#[test]
fn validation_export_does_not_overwrite_existing_measurements()
-> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    let trace = directory.path().join("read.ab1");

    write_reference(&reference, &format!("TTTT{QUERY}CCCC"))?;
    write_config(&config, "linear")?;
    write_abif(&trace, QUERY)?;

    for expected_success in [true, false] {
        let mut command = Command::new(env!("CARGO_BIN_EXE_signal-validation"));
        let assert = command
            .current_dir(directory.path())
            .env("SIGNAL_CONFIG", &config)
            .arg(SAMPLE_ID)
            .arg(&trace)
            .arg("--reference")
            .arg(&reference)
            .assert();
        if expected_success {
            assert.success();
        } else {
            assert
                .failure()
                .stderr(predicate::str::contains("target already exists"));
        }
    }

    Ok(())
}

fn reverse_complement(sequence: &str) -> String {
    sequence
        .chars()
        .rev()
        .map(|base| match base {
            'A' => 'T',
            'C' => 'G',
            'G' => 'C',
            'T' => 'A',
            other => panic!("unsupported synthetic base {other}"),
        })
        .collect()
}
