//! Sample-level evidence aggregation in reference-coordinate and variant space.

mod aggregate;
mod call_evidence;
mod coverage;
mod differences;
mod overlap;
mod variants;

pub(crate) use aggregate::aggregate;
