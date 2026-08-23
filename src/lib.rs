#![forbid(unsafe_code)]

//! Library boundary for the one-AB1 Signal analysis pipeline.
//!
//! The final module graph and child-file plan are documented in
//! `docs/source-layout.md`. `lib.rs` remains the minimal dispatcher: it exposes
//! stable boundary types, routes one [`cli::Command::Analyze`], and keeps
//! configuration, input decoding, scientific stages, and reporting behind the
//! pipeline boundary.

mod alignment;
mod basecalling;
mod checksum;
pub mod cli;
pub mod config;
pub mod error;
mod logger;
pub mod model;
mod pipeline;
mod quality_control;
mod reference;
mod report;
mod signal_processing;
mod trace;
mod variant_calling;

use cli::{Cli, Command};
use error::Result;

/// Dispatches a parsed command through the application boundary.
pub fn run(cli: Cli) -> Result<()> {
    match cli.command {
        Command::Analyze(args) => pipeline::analyze(&args),
    }
}
