//! Normalized primary-sequence SNVs and small indels.

mod extract;
mod mapping;
mod normalize;

pub(crate) use extract::call;
