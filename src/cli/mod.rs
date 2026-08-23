//! Command-line argument definitions for one-file analysis.
//!
//! The MVP keeps this module in `mod.rs`: one positional AB1 path and one
//! required `--reference` FASTA path. Output is derived deterministically as
//! `results/<trace-stem>.json`. Directories, manifests, globs, lists, and repeated
//! trace arguments are not accepted. Configuration is selected by `SIGNAL_CONFIG`.

use std::path::PathBuf;

use clap::{Args, Parser, Subcommand};

/// Signal command-line interface.
#[derive(Debug, Parser)]
#[command(name = "signal", version, about = "Analyze Sanger sequencing traces")]
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
}

/// Arguments for the end-to-end MVP analysis pipeline.
#[derive(Debug, Args)]
pub struct AnalyzeArgs {
    /// Input ABIF/AB1 trace.
    pub trace: PathBuf,

    /// Single-contig reference FASTA.
    #[arg(long)]
    pub reference: PathBuf,
}
