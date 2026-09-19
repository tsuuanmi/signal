#![forbid(unsafe_code)]
#![deny(deprecated)]

//! Command-line boundary for local Signal validation measurement export.

use std::path::PathBuf;
use std::process::ExitCode;

use clap::Parser;
use signal::validation::{self, ValidationExportRequest};

#[derive(Debug, Parser)]
#[command(
    name = "signal-validation",
    version,
    about = "Export local per-locus measurements for Signal validation research"
)]
struct Cli {
    /// Stable non-identifying research sample identifier.
    sample_id: String,

    /// ABIF/AB1 traces belonging to the validation sample.
    #[arg(required = true, num_args = 1..)]
    traces: Vec<PathBuf>,

    /// Single-contig reference FASTA shared by every trace.
    #[arg(long)]
    reference: PathBuf,
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    let request = ValidationExportRequest {
        sample_id: cli.sample_id,
        traces: cli.traces,
        reference: cli.reference,
    };
    match validation::export(request) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::FAILURE
        }
    }
}
