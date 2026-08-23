//! Typed deterministic JSON reporting and atomic publication.

mod atomic;
mod json;
mod variant;

pub(crate) use atomic::publish;
pub(crate) use json::{CompletedAnalysis, build, serialize};
