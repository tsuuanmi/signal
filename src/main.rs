#![forbid(unsafe_code)]

//! Operating-system boundary for the Signal binary.
//!
//! This file remains single-purpose: parse one command, call the library, print
//! a concise error, and return an exit code. It never scans `data/`, parses
//! `.env`, loads scientific configuration, or runs algorithms itself.

use std::process::ExitCode;

use clap::Parser;
use signal::cli::Cli;

fn main() -> ExitCode {
    match signal::run(Cli::parse()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::FAILURE
        }
    }
}
