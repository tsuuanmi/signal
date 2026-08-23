//! End-to-end scientific stage sequencing.

use crate::alignment;
use crate::basecalling;
use crate::cli::AnalyzeArgs;
use crate::error::Result;
use crate::pipeline::input;
use crate::quality_control;
use crate::report::{self, CompletedAnalysis};
use crate::variant_calling;

/// Runs one complete AB1-to-JSON analysis.
pub(crate) fn run(args: &AnalyzeArgs) -> Result<()> {
    let inputs = input::load(args)?;
    let calls = basecalling::call(&inputs.trace, &inputs.config.basecalling)?;
    let quality = quality_control::analyze(&inputs.trace, &calls, &inputs.config.quality_control)?;
    let alignment = alignment::align_best(&quality, &inputs.reference, &inputs.config.alignment)?;
    let variants = variant_calling::call(
        &alignment,
        &inputs.reference,
        &inputs.config.variant_calling,
    )?;
    let output = inputs.output.clone();
    let result = report::build(CompletedAnalysis {
        config: inputs.config,
        trace: inputs.trace,
        reference: inputs.reference,
        calls,
        quality,
        alignment,
        variants,
    })?;
    let bytes = report::serialize(&result)?;
    report::publish(&output, &bytes)
}
