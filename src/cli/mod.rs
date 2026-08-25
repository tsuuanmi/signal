//! Command-line argument definitions for one-file trace operations.
//!
//! Both commands accept one positional AB1 path. `analyze` additionally requires
//! one reference FASTA. Output paths are derived deterministically; directories,
//! manifests, globs, lists, and repeated trace arguments are not accepted.
//! Configuration is selected by `SIGNAL_CONFIG`.

use std::path::PathBuf;

use clap::{Args, Parser, Subcommand};

/// Signal command-line interface.
#[derive(Debug, Parser)]
#[command(name = "signal", version, about = "Process Sanger sequencing traces")]
pub struct Cli {
    /// Operation to run.
    #[command(subcommand)]
    pub command: Command,
}

/// Supported top-level commands.
#[derive(Debug, Subcommand)]
pub enum Command {
    /// Analyze one AB1 trace against a reference FASTA.
    Analyze(AnalyzeArgs),
    /// Re-call and quality-trim one AB1 trace without a reference.
    Basecall(BasecallArgs),
}

/// Arguments for the end-to-end reference analysis pipeline.
#[derive(Debug, Args)]
pub struct AnalyzeArgs {
    /// Input ABIF/AB1 trace.
    pub trace: PathBuf,

    /// Single-contig reference FASTA.
    #[arg(long)]
    pub reference: PathBuf,
}

/// Arguments for reference-free base re-calling and trimming.
#[derive(Debug, Args)]
pub struct BasecallArgs {
    /// Input ABIF/AB1 trace.
    pub trace: PathBuf,
}
