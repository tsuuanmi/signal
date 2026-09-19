mod support;

use std::fs;
use std::path::{Path, PathBuf};

use assert_cmd::Command;
use predicates::prelude::*;
use serde_json::Value;
use tempfile::tempdir;

use support::{write_abif, write_abif_with_secondary_signal, write_config, write_reference};

const QUERY: &str = "ACGTCAGTACGATCGTACCTGAGTACGA";
const SAMPLE_ID: &str = "sample-1";

#[test]
fn writes_deterministic_compact_sample_evidence_v4() -> Result<(), Box<dyn std::error::Error>> {
    let first = tempdir()?;
    let second = tempdir()?;

    for (directory, reverse_order) in [(first.path(), false), (second.path(), true)] {
        let reference = directory.join("reference.fa");
        let config = directory.join("signal.toml");
        let forward = directory.join("read-forward.ab1");
        let reverse = directory.join("read-reverse.ab1");

        let mut alternate = QUERY.as_bytes().to_vec();
        alternate[10] = b'A';
        let alternate = String::from_utf8(alternate)?;
        let reverse_alternate = reverse_complement(&alternate);

        write_reference(&reference, &format!("TTTT{QUERY}CCCC"))?;
        write_config(&config, "linear")?;
        write_abif(&forward, QUERY)?;
        write_abif(&reverse, &reverse_alternate)?;

        let traces = if reverse_order {
            [&reverse, &forward]
        } else {
            [&forward, &reverse]
        };
        run(&traces, &reference, &config, directory)?
            .success()
            .stdout(predicate::str::is_empty())
            .stderr(predicate::str::is_empty());
    }

    let first_bytes = fs::read(sample_output_path(first.path()))?;
    let second_bytes = fs::read(sample_output_path(second.path()))?;
    assert_eq!(first_bytes, second_bytes);

    let value: Value = serde_json::from_slice(&first_bytes)?;
    assert_eq!(value["schema_version"], "signal.sample_evidence/v4");
    assert_eq!(value["sample_id"], SAMPLE_ID);
    assert_object_keys(
        &value,
        &[
            "schema_version",
            "sample_id",
            "provenance",
            "reads",
            "overlaps",
            "locus_differences",
            "variants",
        ],
    )?;
    assert!(value.get("loci").is_none());

    let reads = value["reads"].as_array().ok_or("reads must be an array")?;
    assert_eq!(reads.len(), 2);
    let forward_read = read_by_name(reads, "read-forward")?;
    let reverse_read = read_by_name(reads, "read-reverse")?;
    assert_eq!(forward_read["alignment"]["orientation"], "forward");
    assert_eq!(reverse_read["alignment"]["orientation"], "reverse");

    let overlaps = value["overlaps"]
        .as_array()
        .ok_or("overlaps must be an array")?;
    assert_eq!(overlaps.len(), 1);
    let overlap = &overlaps[0];
    let pair = [
        overlap["left"]
            .as_str()
            .ok_or("overlap left must be a string")?,
        overlap["right"]
            .as_str()
            .ok_or("overlap right must be a string")?,
    ];
    assert!(pair.contains(&"read-forward"));
    assert!(pair.contains(&"read-reverse"));
    assert_eq!(overlap["shared_positions"], QUERY.len());
    assert_eq!(overlap["comparable_bases"], QUERY.len());
    assert_eq!(overlap["agreements"], QUERY.len() - 1);
    assert_eq!(overlap["conflicts"], 1);
    let agreement = overlap["agreement"]
        .as_f64()
        .ok_or("overlap agreement must be numeric")?;
    let expected_agreement = (QUERY.len() - 1) as f64 / QUERY.len() as f64;
    assert!((agreement - expected_agreement).abs() < 1e-12);
    assert_eq!(overlap["eligible"], true);
    assert_eq!(overlap["exclusion_reasons"], serde_json::json!([]));

    let differences = value["locus_differences"]
        .as_array()
        .ok_or("locus_differences must be an array")?;
    assert_eq!(differences.len(), 1);
    let difference = &differences[0];
    assert_eq!(difference["position"], 15);
    assert_eq!(difference["reference"], "G");
    let observations = difference["observations"]
        .as_array()
        .ok_or("observations must be an array")?;
    assert_eq!(observations.len(), 2);
    let forward_observation = observation_for_read(observations, "read-forward")?;
    let reverse_observation = observation_for_read(observations, "read-reverse")?;
    assert_eq!(forward_observation["state"], "reference");
    assert_eq!(forward_observation["base"], "G");
    assert_eq!(reverse_observation["state"], "alternate");
    assert_eq!(reverse_observation["base"], "A");

    let variants = value["variants"]
        .as_array()
        .ok_or("variants must be an array")?;
    assert_eq!(variants.len(), 1);
    let variant = &variants[0];
    assert_eq!(variant["position"], 15);
    assert_eq!(variant["reference"], "G");
    assert_eq!(variant["alternate"], "A");
    assert_eq!(variant["kind"], "SNV");
    let support = variant["support"]
        .as_array()
        .ok_or("variant support must be an array")?;
    assert_eq!(support.len(), 1);
    assert_eq!(support[0]["read"], "read-reverse");
    assert_eq!(support[0]["eligible"], true);
    assert_eq!(support[0]["exclusion_reasons"], serde_json::json!([]));
    let call = &support[0]["calls"][0];
    assert_eq!(call["role"], "supporting");
    assert_eq!(call["base"], "A");
    assert_eq!(call["peaks"]["A"], 1000);
    assert!(call["quality"].is_number());
    assert!(call.get("index").is_none());
    assert!(call.get("position").is_none());
    assert!(call.get("ploc").is_none());

    let text = std::str::from_utf8(&first_bytes)?;
    for repeated in ["read_name", "read_sha256", "\"loci\""] {
        assert!(!text.contains(repeated));
    }

    Ok(())
}

#[test]
fn preserves_mixed_snv_as_ineligible_sample_evidence() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let reference = directory.path().join("reference.fa");
    let config = directory.path().join("signal.toml");
    let trace = directory.path().join("mixed-read.ab1");
    let mut query = QUERY.to_owned();
    query.replace_range(10..11, "T");

    write_reference(&reference, &format!("TTTT{QUERY}CCCC"))?;
    write_config(&config, "linear")?;
    let config_text = fs::read_to_string(&config)?;
    fs::write(
        &config,
        config_text.replace("best_section_fraction=0.10", "best_section_fraction=1.0"),
    )?;
    write_abif_with_secondary_signal(&trace, &query, 10, b'C', 400)?;

    let mut command = Command::new(env!("CARGO_BIN_EXE_signal"));
    command
        .current_dir(directory.path())
        .env("SIGNAL_CONFIG", &config)
        .arg("sample")
        .arg(SAMPLE_ID)
        .arg(&trace)
        .arg("--reference")
        .arg(&reference)
        .assert()
        .success();

    let value: Value = serde_json::from_slice(&fs::read(sample_output_path(directory.path()))?)?;
    assert_eq!(value["schema_version"], "signal.sample_evidence/v4");
    assert_eq!(value["overlaps"], serde_json::json!([]));
    let variants = value["variants"]
        .as_array()
        .ok_or("variants must be an array")?;
    assert_eq!(variants.len(), 1);
    let support = variants[0]["support"]
        .as_array()
        .ok_or("support must be an array")?;
    assert_eq!(support.len(), 1);
    assert_eq!(support[0]["read"], "mixed-read");
    assert_eq!(support[0]["eligible"], false);
    let reasons = support[0]["exclusion_reasons"]
        .as_array()
        .ok_or("exclusion_reasons must be an array")?;
    assert!(
        reasons
            .iter()
            .any(|reason| reason == "mixed_supporting_signal")
    );
    let call = &support[0]["calls"][0];
    assert_eq!(call["base"], "T");
    assert_eq!(call["peaks"]["T"], 1000);
    assert_eq!(call["peaks"]["C"], 400);
    Ok(())
}

fn run(
    traces: &[&PathBuf; 2],
    reference: &Path,
    config: &Path,
    workdir: &Path,
) -> Result<assert_cmd::assert::Assert, Box<dyn std::error::Error>> {
    let mut command = Command::new(env!("CARGO_BIN_EXE_signal"));
    command
        .current_dir(workdir)
        .env("SIGNAL_CONFIG", config)
        .arg("sample")
        .arg(SAMPLE_ID);
    for trace in traces {
        command.arg(trace);
    }
    Ok(command.arg("--reference").arg(reference).assert())
}

fn sample_output_path(workdir: &Path) -> PathBuf {
    workdir
        .join("results")
        .join(format!("{SAMPLE_ID}.sample.json"))
}

fn read_by_name<'a>(
    reads: &'a [Value],
    name: &str,
) -> Result<&'a Value, Box<dyn std::error::Error>> {
    reads
        .iter()
        .find(|read| read["name"] == name)
        .ok_or_else(|| format!("missing read {name}").into())
}

fn observation_for_read<'a>(
    observations: &'a [Value],
    read: &str,
) -> Result<&'a Value, Box<dyn std::error::Error>> {
    observations
        .iter()
        .find(|observation| observation["read"] == read)
        .ok_or_else(|| format!("missing observation for read {read}").into())
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

fn assert_object_keys(value: &Value, expected: &[&str]) -> Result<(), Box<dyn std::error::Error>> {
    let object = value.as_object().ok_or("expected object")?;
    let keys = object
        .keys()
        .map(String::as_str)
        .collect::<std::collections::BTreeSet<_>>();
    let expected = expected.iter().copied().collect();
    assert_eq!(keys, expected);
    Ok(())
}
