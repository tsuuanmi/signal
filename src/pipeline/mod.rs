//! End-to-end orchestration for one AB1, one FASTA, and one JSON result.

mod analyze;
mod input;

use crate::cli::AnalyzeArgs;
use crate::error::Result;

/// Runs the focused one-file analysis pipeline.
pub(crate) fn analyze(args: &AnalyzeArgs) -> Result<()> {
    analyze::run(args)
}
