//! Explicit validation tooling boundary for local threshold research.

use std::path::PathBuf;

use crate::error::Result;

#[derive(Debug)]
pub struct ValidationExportRequest {
    pub sample_id: String,
    pub traces: Vec<PathBuf>,
    pub reference: PathBuf,
}

pub fn export(request: ValidationExportRequest) -> Result<()> {
    crate::pipeline::validation_export(&request)
}
