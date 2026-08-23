mod support;

use std::fs;
use std::path::Path;

use assert_cmd::Command;
use predicates::prelude::*;
use serde_json::Value;
use tempfile::tempdir;

use support::{
    output_path, write_abif, write_abif_with_channel_order, write_abif_with_ploc,
    write_abif_with_short_pbas, write_abif_with_unused_p2ba, write_abif_with_vendor, write_config,
    write_reference,
};

const QUERY: &str = "ACGTCAGTACGATCGTACCTGAGTACGA";

#[test]
fn writes_deterministic_compact_json() -> Result<(), Box<dyn std::error::Error>> {
    let first = tempdir()?;
    let second = tempdir()?;
    for directory in [first.path(), second.path()] {
        let trace = directory.join("trace.ab1");
        let reference = directory.join("reference.fa");
        let config = directory.join("signal.toml");
        write_abif(&trace, QUERY)?;
        write_reference(&reference, &format!("TTTT{QUERY}CCCC"))?;
        write_config(&config, "linear")?;
        run(&trace, &reference, &config, directory)?.success();
    }

    let first_bytes = fs::read(output_path(first.path(), &first.path().join("trace.ab1")))?;
    let second_bytes = fs::read(output_path(second.path(), &second.path().join("trace.ab1")))?;
    assert_eq!(first_bytes, second_bytes);
    let value: Value = serde_json::from_slice(&first_bytes)?;
    assert_eq!(value["schema_version"], "signal.analysis/v3");
    assert_eq!(value["alignment"]["orientation"], "forward");
    assert_eq!(
        value["meta"]["methods"]["basecalling"],
        "signal.peak_recall/v2"
    );
    assert_eq!(
        value["meta"]["methods"]["variant_calling"],
        "signal.primary_difference/v2"
    );
    assert!(value.get("analysis").is_none());
    assert!(value.pointer("/meta/input/size_bytes").is_none());
    let text = std::str::from_utf8(&first_bytes)?;
    for obsolete in ["evidence", "position_1based", "_0based", "_exclusive"] {
        assert!(!text.contains(obsolete));
    }
    assert!(!first.path().join("results/trace.vcf").exists());
    Ok(())
}

#[test]
fn reorders_noncanonical_fwo_channels() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    write_abif_with_channel_order(&trace, QUERY, *b"TGCA")?;
    write_reference(&reference, &format!("TTTT{QUERY}CCCC"))?;
    write_config(&config, "linear")?;

    run(&trace, &reference, &config, directory.path())?.success();
    let value = read_result(directory.path(), &trace)?;
    assert_eq!(value["sequence"]["primary"], QUERY);
    assert_eq!(value["variants"].as_array().map(Vec::len), Some(0));
    Ok(())
}

#[test]
fn ignores_unused_p2ba_content() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    write_abif_with_unused_p2ba(&trace, QUERY, vec![b'!'])?;
    write_reference(&reference, &format!("TTTT{QUERY}CCCC"))?;
    write_config(&config, "linear")?;

    run(&trace, &reference, &config, directory.path())?.success();
    Ok(())
}

#[test]
fn rejects_non_increasing_ploc_without_output() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    let mut ploc: Vec<usize> = (0..QUERY.len()).map(|index| 2 + 4 * index).collect();
    ploc[5] = ploc[4];
    write_abif_with_ploc(&trace, QUERY, ploc)?;
    write_reference(&reference, &format!("TTTT{QUERY}CCCC"))?;
    write_config(&config, "linear")?;

    run(&trace, &reference, &config, directory.path())?
        .failure()
        .stderr(predicate::str::contains("strictly increasing"));
    assert!(!output_path(directory.path(), &trace).exists());
    Ok(())
}

#[test]
fn rejects_out_of_range_ploc_without_output() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    let mut ploc: Vec<usize> = (0..QUERY.len()).map(|index| 2 + 4 * index).collect();
    *ploc.last_mut().ok_or("missing synthetic PLOC")? = 30_000;
    write_abif_with_ploc(&trace, QUERY, ploc)?;
    write_reference(&reference, &format!("TTTT{QUERY}CCCC"))?;
    write_config(&config, "linear")?;

    run(&trace, &reference, &config, directory.path())?
        .failure()
        .stderr(predicate::str::contains("outside channel samples"));
    assert!(!output_path(directory.path(), &trace).exists());
    Ok(())
}

#[test]
fn rejects_vendor_length_mismatch_without_output() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    write_abif_with_short_pbas(&trace, QUERY)?;
    write_reference(&reference, &format!("TTTT{QUERY}CCCC"))?;
    write_config(&config, "linear")?;

    run(&trace, &reference, &config, directory.path())?
        .failure()
        .stderr(predicate::str::contains("PBAS.2 length"));
    assert!(!output_path(directory.path(), &trace).exists());
    Ok(())
}

#[test]
fn reports_snv_with_peaks_and_quality() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    write_abif(&trace, QUERY)?;
    let mut reference_query = QUERY.as_bytes().to_vec();
    reference_query[10] = if reference_query[10] == b'A' {
        b'C'
    } else {
        b'A'
    };
    write_reference(
        &reference,
        &format!("TTTT{}CCCC", String::from_utf8(reference_query)?),
    )?;
    write_config(&config, "linear")?;

    run(&trace, &reference, &config, directory.path())?.success();
    let value = read_result(directory.path(), &trace)?;
    let variants = value["variants"]
        .as_array()
        .ok_or("variants is not an array")?;
    assert_eq!(variants.len(), 1);
    let variant = &variants[0];
    assert_eq!(variant["kind"], "SNV");
    assert_eq!(variant["position"], 15);
    assert_eq!(variant["classification"], "primary_sequence_difference");
    assert!(variant.get("evidence").is_none());
    let call = &variant["calls"][0];
    assert_eq!(call["role"], "supporting");
    assert_eq!(call["index"], 10);
    assert_eq!(call["position"], 15);
    assert_eq!(call["ploc"], 42);
    for base in ["A", "C", "G", "T"] {
        assert!(call["peaks"][base]["height"].is_number());
        assert_eq!(call["peaks"][base]["position"], 42);
    }
    assert_eq!(call["peaks"]["G"]["height"], 1000);
    assert!(call["quality"]["relative_score"].is_number());
    assert_eq!(call["quality"]["phred_calibrated"], false);
    Ok(())
}

#[test]
fn maps_reverse_snv_to_original_call_and_ploc() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    let mut biological_query = QUERY.to_owned();
    biological_query.replace_range(10..11, "T");
    write_abif(&trace, &reverse_complement(&biological_query))?;
    write_reference(&reference, &format!("TTTT{QUERY}CCCC"))?;
    write_config(&config, "linear")?;

    run(&trace, &reference, &config, directory.path())?.success();
    let value = read_result(directory.path(), &trace)?;
    assert_eq!(value["alignment"]["orientation"], "reverse");
    let variant = &value["variants"][0];
    assert_eq!(variant["position"], 15);
    assert_eq!(variant["reference"], "G");
    assert_eq!(variant["alternate"], "T");
    let call = &variant["calls"][0];
    assert_eq!(call["index"], 17);
    assert_eq!(call["position"], 15);
    assert_eq!(call["ploc"], 70);
    assert_eq!(call["primary"], "A");
    assert_eq!(call["peaks"]["A"]["height"], 1000);
    Ok(())
}

#[test]
fn reports_insertion_support_and_flanks() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    write_abif(&trace, QUERY)?;
    let reference_query = format!("{}{}", &QUERY[..12], &QUERY[13..]);
    write_reference(&reference, &format!("TTTT{reference_query}CCCC"))?;
    write_config(&config, "linear")?;

    run(&trace, &reference, &config, directory.path())?.success();
    let value = read_result(directory.path(), &trace)?;
    let variant = &value["variants"][0];
    assert_eq!(variant["kind"], "INS");
    assert_eq!(variant["position"], 16);
    assert_eq!(variant["reference"], "A");
    assert_eq!(variant["alternate"], "AT");
    let calls = variant["calls"].as_array().ok_or("calls is not an array")?;
    assert_eq!(calls.len(), 3);
    assert_eq!(calls[0]["role"], "supporting");
    assert_eq!(calls[0]["index"], 12);
    assert!(calls[0].get("position").is_none());
    assert_eq!(calls[0]["ploc"], 50);
    assert_eq!(calls[1]["role"], "flanking");
    assert_eq!(calls[1]["index"], 11);
    assert_eq!(calls[1]["position"], 16);
    assert_eq!(calls[1]["ploc"], 46);
    assert_eq!(calls[2]["role"], "flanking");
    assert_eq!(calls[2]["index"], 13);
    assert_eq!(calls[2]["position"], 17);
    assert_eq!(calls[2]["ploc"], 54);
    Ok(())
}

#[test]
fn reports_deletion_with_flanks_only() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    write_abif(&trace, QUERY)?;
    let reference_query = format!("{}A{}", &QUERY[..12], &QUERY[12..]);
    write_reference(&reference, &format!("TTTT{reference_query}CCCC"))?;
    write_config(&config, "linear")?;

    run(&trace, &reference, &config, directory.path())?.success();
    let value = read_result(directory.path(), &trace)?;
    let variant = &value["variants"][0];
    assert_eq!(variant["kind"], "DEL");
    assert_eq!(variant["position"], 15);
    assert_eq!(variant["reference"], "GA");
    assert_eq!(variant["alternate"], "G");
    let calls = variant["calls"].as_array().ok_or("calls is not an array")?;
    assert_eq!(calls.len(), 2);
    assert!(calls.iter().all(|item| item["role"] == "flanking"));
    assert_eq!(calls[0]["index"], 10);
    assert_eq!(calls[0]["position"], 15);
    assert_eq!(calls[0]["ploc"], 42);
    assert_eq!(calls[1]["index"], 11);
    assert_eq!(calls[1]["position"], 17);
    assert_eq!(calls[1]["ploc"], 46);
    Ok(())
}

#[test]
fn represents_circular_origin_wrap() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    let rotated = format!("{}{}", &QUERY[18..], &QUERY[..18]);
    write_abif(&trace, &rotated)?;
    write_reference(&reference, QUERY)?;
    write_config(&config, "circular")?;

    run(&trace, &reference, &config, directory.path())?.success();
    let value = read_result(directory.path(), &trace)?;
    assert_eq!(value["alignment"]["wraps_origin"], true);
    assert_eq!(
        value["alignment"]["reference_segments"]
            .as_array()
            .map(Vec::len),
        Some(2)
    );
    assert_eq!(value["alignment"]["reference_segments"][0]["start"], 18);
    assert_eq!(value["alignment"]["reference_segments"][0]["end"], 28);
    assert_eq!(value["alignment"]["reference_segments"][1]["start"], 0);
    assert_eq!(value["alignment"]["reference_segments"][1]["end"], 18);
    assert_eq!(value["warnings"]["reference_origin_wrap"], true);
    Ok(())
}

#[test]
fn maps_circular_origin_snv_to_original_call_and_ploc() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    let mut rotated = format!("{}{}", &QUERY[18..], &QUERY[..18]);
    rotated.replace_range(12..13, "A");
    write_abif(&trace, &rotated)?;
    write_reference(&reference, QUERY)?;
    write_config(&config, "circular")?;

    run(&trace, &reference, &config, directory.path())?.success();
    let value = read_result(directory.path(), &trace)?;
    assert_eq!(value["alignment"]["wraps_origin"], true);
    let variant = &value["variants"][0];
    assert_eq!(variant["position"], 3);
    assert_eq!(variant["reference"], "G");
    assert_eq!(variant["alternate"], "A");
    let call = &variant["calls"][0];
    assert_eq!(call["index"], 12);
    assert_eq!(call["position"], 3);
    assert_eq!(call["ploc"], 50);
    Ok(())
}

#[test]
fn accepts_iupac_vendor_calls_and_char_pcon() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    let mut vendor = QUERY.to_owned();
    vendor.replace_range(5..6, "K");
    write_abif_with_vendor(&trace, QUERY, &vendor, 2)?;
    let mut reference_query = QUERY.to_owned();
    reference_query.replace_range(5..6, if &QUERY[5..6] == "A" { "C" } else { "A" });
    write_reference(&reference, &format!("TTTT{reference_query}CCCC"))?;
    write_config(&config, "linear")?;

    run(&trace, &reference, &config, directory.path())?.success();
    let value = read_result(directory.path(), &trace)?;
    let call = &value["variants"][0]["calls"][0];
    assert_eq!(call["index"], 5);
    assert_eq!(call["position"], 10);
    assert_eq!(call["ploc"], 22);
    assert_eq!(call["quality"]["vendor_score"], 40);
    assert_eq!(call["quality"]["vendor_score_applies"], false);
    Ok(())
}

#[test]
fn malformed_abif_leaves_no_output() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    fs::write(&trace, b"not an ABIF file")?;
    write_reference(&reference, &format!("TTTT{QUERY}CCCC"))?;
    write_config(&config, "linear")?;

    run(&trace, &reference, &config, directory.path())?
        .failure()
        .stderr(predicate::str::contains("invalid ABIF input"));
    assert!(!output_path(directory.path(), &trace).exists());
    Ok(())
}

#[test]
fn refuses_to_overwrite_completed_output() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    write_abif(&trace, QUERY)?;
    write_reference(&reference, &format!("TTTT{QUERY}CCCC"))?;
    write_config(&config, "linear")?;
    let output = output_path(directory.path(), &trace);
    fs::create_dir_all(output.parent().ok_or("output has no parent")?)?;
    fs::write(&output, b"owned")?;

    run(&trace, &reference, &config, directory.path())?
        .failure()
        .stderr(predicate::str::contains("target already exists"));
    assert_eq!(fs::read(output)?, b"owned");
    Ok(())
}

fn read_result(workdir: &Path, trace: &Path) -> Result<Value, Box<dyn std::error::Error>> {
    Ok(serde_json::from_slice(&fs::read(output_path(
        workdir, trace,
    ))?)?)
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
            _ => 'N',
        })
        .collect()
}

fn run(
    trace: &Path,
    reference: &Path,
    config: &Path,
    workdir: &Path,
) -> Result<assert_cmd::assert::Assert, Box<dyn std::error::Error>> {
    let mut command = Command::new(env!("CARGO_BIN_EXE_signal"));
    Ok(command
        .current_dir(workdir)
        .env("SIGNAL_CONFIG", config)
        .arg("analyze")
        .arg(trace)
        .arg("--reference")
        .arg(reference)
        .assert())
}
