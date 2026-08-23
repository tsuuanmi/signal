mod support;

use std::collections::BTreeSet;
use std::fs;
use std::path::Path;

use assert_cmd::Command;
use predicates::prelude::*;
use serde_json::Value;
use tempfile::tempdir;

use support::{
    output_path, write_abif, write_abif_with_background_noise, write_abif_with_channel_order,
    write_abif_with_peak_heights, write_abif_with_ploc, write_abif_with_short_pbas,
    write_abif_with_unused_p2ba, write_abif_with_vendor, write_config, write_reference,
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
        run(&trace, &reference, &config, directory)?
            .success()
            .stdout(predicate::str::is_empty())
            .stderr(predicate::str::is_empty());
    }

    let first_bytes = fs::read(output_path(first.path(), &first.path().join("trace.ab1")))?;
    let second_bytes = fs::read(output_path(second.path(), &second.path().join("trace.ab1")))?;
    assert_eq!(first_bytes, second_bytes);
    let value: Value = serde_json::from_slice(&first_bytes)?;
    assert_eq!(value["schema_version"], "signal.analysis/v5");
    assert_object_keys(
        &value,
        &[
            "schema_version",
            "provenance",
            "read",
            "signal_quality",
            "alignment",
            "variants",
            "warnings",
        ],
    );
    assert_object_keys(
        &value["provenance"],
        &[
            "software_version",
            "input",
            "reference",
            "configuration_sha256",
        ],
    );
    assert_object_keys(&value["read"], &["call_count", "trim"]);
    assert_object_keys(
        &value["alignment"],
        &[
            "orientation",
            "callable_bases",
            "identity",
            "unresolved_bases",
            "gap_opens",
            "reference_segments",
            "wraps_origin",
        ],
    );
    assert_object_keys(
        &value["warnings"],
        &[
            "unresolved_primary_calls",
            "multi_channel_unresolved_calls",
            "excluded_variant_candidates",
        ],
    );
    assert_eq!(value["read"]["call_count"], 28);
    assert_eq!(value["alignment"]["orientation"], "forward");
    assert!(value["signal_quality"]["noisy_regions"].is_array());
    assert!(value.get("meta").is_none());
    assert!(value.get("sequence").is_none());
    assert!(value.pointer("/signal_quality/windows").is_none());
    let text = std::str::from_utf8(&first_bytes)?;
    for obsolete in ["evidence", "position_1based", "_0based", "_exclusive"] {
        assert!(!text.contains(obsolete));
    }
    assert!(!first.path().join("results/trace.vcf").exists());
    let log = fs::read_to_string(first.path().join("logs/trace.log"))?;
    let mut search_start = 0;
    for event in [
        "event=analysis_started",
        "event=inputs_loaded",
        "event=basecalling_completed",
        "event=signal_processing_completed",
        "event=quality_control_completed",
        "event=alignment_completed",
        "event=variant_calling_completed",
        "event=result_ready_for_publication",
    ] {
        let offset = log[search_start..]
            .find(event)
            .ok_or_else(|| format!("missing ordered log event {event}"))?;
        search_start += offset + event.len();
    }
    assert!(log.lines().all(|line| line.contains("run_id=")));
    assert!(log.contains("calls=28 canonical_primary=28 unresolved_primary=0"));
    assert!(log.contains("retained=28"));
    assert!(log.contains(
        "windows=19 noisy_windows=0 noisy_regions=0 noisy_calls=0 window_size_bases=10 minimum_noisy_windows=2"
    ));
    assert!(log.contains("orientation=Forward"));
    assert!(log.contains("reported=0 snv=0 insertion=0 deletion=0 excluded=0"));
    assert!(log.contains("minimum_peak_height=150"));
    assert!(!log.contains(QUERY));
    assert!(!log.contains("[[1, 50000]]"));
    assert!(!log.contains("\"schema_version\""));
    assert!(!log.contains("gapped_query"));
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
    assert_eq!(value["read"]["call_count"], QUERY.len());
    assert_eq!(value["alignment"]["identity"], 1.0);
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
    assert_object_keys(
        variant,
        &["position", "reference", "alternate", "kind", "calls"],
    );
    assert_eq!(variant["kind"], "SNV");
    assert_eq!(variant["position"], 15);
    let call = &variant["calls"][0];
    assert_object_keys(
        call,
        &[
            "role",
            "index",
            "position",
            "ploc",
            "primary",
            "ambiguity",
            "maximum_peak_height",
            "relative_quality",
        ],
    );
    assert_eq!(call["role"], "supporting");
    assert_eq!(call["index"], 10);
    assert_eq!(call["position"], 15);
    assert_eq!(call["ploc"], 42);
    assert_eq!(call["maximum_peak_height"], 1000);
    assert!(call["relative_quality"].is_number());
    Ok(())
}

#[test]
fn annotates_noisy_region_without_filtering_supported_snv() -> Result<(), Box<dyn std::error::Error>>
{
    let low_threshold = tempdir()?;
    let high_threshold = tempdir()?;
    let mut query = QUERY.to_owned();
    query.replace_range(10..11, "T");
    let mut results = Vec::new();

    for (directory, threshold) in [(&low_threshold, 0.1), (&high_threshold, 10_000.0)] {
        let trace = directory.path().join("trace.ab1");
        let reference = directory.path().join("reference.fa");
        let config = directory.path().join("signal.toml");
        write_abif_with_background_noise(&trace, &query, 7..14, 300)?;
        write_reference(&reference, &format!("TTTT{QUERY}CCCC"))?;
        write_config(&config, "linear")?;
        let config_text = fs::read_to_string(&config)?;
        fs::write(
            &config,
            config_text.replace(
                "minimum_primary_snr=3.0",
                &format!("minimum_primary_snr={threshold}"),
            ),
        )?;
        run(&trace, &reference, &config, directory.path())?.success();
        results.push(read_result(directory.path(), &trace)?);
    }

    assert_eq!(results[0]["read"], results[1]["read"]);
    assert_eq!(results[0]["alignment"], results[1]["alignment"]);
    assert_eq!(results[0]["variants"], results[1]["variants"]);
    assert!(
        results[0]["signal_quality"]["noisy_regions"]
            .as_array()
            .is_some_and(Vec::is_empty)
    );

    let variants = results[1]["variants"]
        .as_array()
        .ok_or("variants is not an array")?;
    assert_eq!(variants.len(), 1);
    assert_eq!(variants[0]["kind"], "SNV");
    assert_eq!(variants[0]["calls"][0]["index"], 10);
    let regions = results[1]["signal_quality"]["noisy_regions"]
        .as_array()
        .ok_or("noisy_regions is not an array")?;
    assert!(regions.iter().any(|region| {
        region["calls"]["start"]
            .as_u64()
            .is_some_and(|start| start <= 10)
            && region["calls"]["end"].as_u64().is_some_and(|end| end > 10)
    }));
    assert_eq!(results[1]["warnings"]["excluded_variant_candidates"], 0);
    Ok(())
}

#[test]
fn filters_extracted_snv_below_peak_floor() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    let mut query = QUERY.to_owned();
    query.replace_range(10..11, "T");
    let mut peaks = vec![1000; query.len()];
    peaks[10] = 149;
    write_abif_with_peak_heights(&trace, &query, peaks)?;
    write_reference(&reference, &format!("TTTT{QUERY}CCCC"))?;
    write_config(&config, "linear")?;

    run(&trace, &reference, &config, directory.path())?.success();
    let value = read_result(directory.path(), &trace)?;
    assert_eq!(value["variants"].as_array().map(Vec::len), Some(0));
    assert_eq!(value["warnings"]["excluded_variant_candidates"], 1);
    let log = fs::read_to_string(directory.path().join("logs/trace.log"))?;
    assert!(log.contains("event=variant_calling_completed"));
    assert!(log.contains("reported=0 snv=0 insertion=0 deletion=0 excluded=1"));
    let removed = log
        .lines()
        .find(|line| line.contains("event=variant_removed"))
        .ok_or("missing removed-variant log record")?;
    assert!(removed.contains("kind=SNV contig=\"synthetic\" position=15"));
    assert!(removed.contains("reasons=peak_below_minimum"));
    assert!(!removed.contains("reference="));
    assert!(!removed.contains("alternate="));
    assert!(log.contains(" | WARN     | "));
    assert!(log.contains("event=warning_summary"));
    assert!(log.contains("excluded_variant_candidates=1"));
    Ok(())
}

#[test]
fn filters_by_normalized_anchor_region() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    let mut query = QUERY.to_owned();
    query.replace_range(10..11, "T");
    write_abif(&trace, &query)?;
    write_reference(&reference, &format!("TTTT{QUERY}CCCC"))?;
    write_config(&config, "linear")?;
    let restricted =
        fs::read_to_string(&config)?.replace("regions=[[1, 50000]]", "regions=[[16, 16]]");
    fs::write(&config, restricted)?;

    run(&trace, &reference, &config, directory.path())?.success();
    let value = read_result(directory.path(), &trace)?;
    assert_eq!(value["variants"].as_array().map(Vec::len), Some(0));
    assert_eq!(value["warnings"]["excluded_variant_candidates"], 1);
    let log = fs::read_to_string(directory.path().join("logs/trace.log"))?;
    assert!(log.contains(
        "event=variant_removed kind=SNV contig=\"synthetic\" position=15 reasons=outside_configured_region"
    ));
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
    assert_eq!(call["maximum_peak_height"], 1000);
    Ok(())
}

#[test]
fn reports_insertion_support_and_flanks() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    let mut peaks = vec![1000; QUERY.len()];
    peaks[11] = 1;
    peaks[13] = 1;
    write_abif_with_peak_heights(&trace, QUERY, peaks)?;
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
    assert_eq!(calls[0]["maximum_peak_height"], 1000);
    assert!(calls[0]["relative_quality"].is_number());
    assert_eq!(calls[1]["role"], "flanking");
    assert_eq!(calls[1]["index"], 11);
    assert_eq!(calls[1]["position"], 16);
    assert_eq!(calls[1]["ploc"], 46);
    assert_eq!(calls[2]["role"], "flanking");
    assert_eq!(calls[2]["index"], 13);
    assert_eq!(calls[2]["position"], 17);
    assert_eq!(calls[2]["ploc"], 54);
    for flank in &calls[1..] {
        assert!(flank.get("maximum_peak_height").is_none());
        assert!(flank.get("relative_quality").is_none());
    }
    Ok(())
}

#[test]
fn filters_multibase_insertion_when_any_inserted_peak_is_low()
-> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    let mut peaks = vec![1000; QUERY.len()];
    peaks[13] = 149;
    write_abif_with_peak_heights(&trace, QUERY, peaks)?;
    let reference_query = format!("{}{}", &QUERY[..12], &QUERY[14..]);
    write_reference(&reference, &format!("TTTT{reference_query}CCCC"))?;
    write_config(&config, "linear")?;

    run(&trace, &reference, &config, directory.path())?.success();
    let value = read_result(directory.path(), &trace)?;
    assert_eq!(value["variants"].as_array().map(Vec::len), Some(0));
    assert_eq!(value["warnings"]["excluded_variant_candidates"], 1);
    Ok(())
}

#[test]
fn reports_deletion_with_flanks_only() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let trace = directory.path().join("trace.ab1");
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    let mut peaks = vec![1000; QUERY.len()];
    peaks[10] = 1;
    peaks[11] = 1;
    write_abif_with_peak_heights(&trace, QUERY, peaks)?;
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
    assert!(calls.iter().all(|call| {
        call.get("maximum_peak_height").is_none() && call.get("relative_quality").is_none()
    }));
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
    assert!(value["warnings"].get("reference_origin_wrap").is_none());
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
    assert!(call["relative_quality"].is_number());
    assert!(call.get("quality").is_none());
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
    let log = fs::read_to_string(directory.path().join("logs/trace.log"))?;
    assert!(log.contains(" | ERROR    | "));
    assert!(log.contains("event=analysis_failed stage=input_loading"));
    assert!(log.contains("invalid ABIF input"));
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
    let log = fs::read_to_string(directory.path().join("logs/trace.log"))?;
    assert!(log.contains("event=analysis_started"));
    assert!(log.contains("event=analysis_failed stage=input_loading"));
    assert!(log.contains("target already exists"));
    assert!(log.contains(" | ERROR    | "));
    Ok(())
}

fn assert_object_keys(value: &Value, expected: &[&str]) {
    let actual = value
        .as_object()
        .map(|object| object.keys().map(String::as_str).collect::<BTreeSet<_>>())
        .unwrap_or_default();
    let expected = expected.iter().copied().collect::<BTreeSet<_>>();
    assert_eq!(actual, expected);
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
