//! End-to-end orchestration for one-file Signal operations.

mod analyze;
mod basecall;
mod input;
mod read;

use std::time::Instant;

use crate::cli::{AnalyzeArgs, BasecallArgs};
use crate::error::{Error, Result};
use crate::logger::Logger;

/// Runs one AB1-to-reference analysis.
pub(crate) fn analyze(args: &AnalyzeArgs) -> Result<()> {
    analyze::run(args)
}

/// Runs one reference-free AB1 basecall operation.
pub(crate) fn basecall(args: &BasecallArgs) -> Result<()> {
    basecall::run(args)
}

/// Records a terminal operation failure without discarding either error.
fn record_failure(
    logger: &mut Logger,
    event: &'static str,
    stage: &'static str,
    started: Instant,
    operation: Error,
) -> Error {
    let logging = logger
        .error(
            module_path!(),
            line!(),
            format_args!(
                "event={event} stage={stage} elapsed_ms={} error={:?}",
                started.elapsed().as_millis(),
                operation.to_string()
            ),
        )
        .and_then(|()| logger.sync());
    match logging {
        Ok(()) => operation,
        Err(logging) => Error::OperationAndLog {
            operation: Box::new(operation),
            logging: Box::new(logging),
        },
    }
}
