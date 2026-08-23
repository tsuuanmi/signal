use assert_cmd::Command;
use predicates::prelude::*;
use tempfile::tempdir;

#[test]
fn help_succeeds() {
    let mut command = Command::new(env!("CARGO_BIN_EXE_signal"));
    command
        .arg("--help")
        .assert()
        .success()
        .stdout(predicate::str::contains("Analyze Sanger sequencing traces"));
}

#[test]
fn analyze_requires_arguments() {
    let mut command = Command::new(env!("CARGO_BIN_EXE_signal"));
    command
        .arg("analyze")
        .assert()
        .failure()
        .stderr(predicate::str::contains("Usage:"));
}

#[test]
fn rejects_removed_out_prefix_option() {
    let mut command = Command::new(env!("CARGO_BIN_EXE_signal"));
    command
        .args([
            "analyze",
            "trace.ab1",
            "--reference",
            "reference.fa",
            "--out-prefix",
            "legacy",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "unexpected argument '--out-prefix'",
        ));
}

#[test]
fn missing_trace_fails_explicitly() -> Result<(), Box<dyn std::error::Error>> {
    let directory = tempdir()?;
    let mut command = Command::new(env!("CARGO_BIN_EXE_signal"));
    let log_directory = directory.path().join("custom-logs");
    command
        .current_dir(directory.path())
        .env("SIGNAL_LOG_DIR", &log_directory)
        .args([
            "analyze",
            "missing.ab1",
            "--reference",
            "references/rCRS.fasta",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("failed to read AB1 file"));
    let log = std::fs::read_to_string(log_directory.join("missing.log"))?;
    assert!(log.contains("event=analysis_started"));
    assert!(log.contains("event=analysis_failed stage=input_loading"));
    assert!(log.contains("failed to read AB1 file"));
    Ok(())
}
