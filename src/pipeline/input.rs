//! One-file path validation and input loading.

use std::path::{Path, PathBuf};

use crate::cli::AnalyzeArgs;
use crate::config::{self, Config};
use crate::error::{Error, Result};
use crate::model::reference::Reference;
use crate::model::trace::Chromatogram;
use crate::{reference, trace};

/// Fully loaded inputs and the single output target.
pub(crate) struct Inputs {
    pub(crate) config: Config,
    pub(crate) trace: Chromatogram,
    pub(crate) reference: Reference,
    pub(crate) output: PathBuf,
}

/// Validates cardinality/path types and loads every input exactly once.
pub(crate) fn load(args: &AnalyzeArgs) -> Result<Inputs> {
    require_regular_file(&args.trace, "AB1")?;
    require_regular_file(&args.reference, "reference")?;
    let config = config::load()?;
    require_regular_file(&config.source_path, "configuration")?;
    let output = output_path(&args.trace)?;
    if output.exists() {
        return Err(Error::Path {
            kind: "output",
            path: output,
            reason: "target already exists".into(),
        });
    }
    let parent = output
        .parent()
        .filter(|value| !value.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    if parent.exists() && !parent.is_dir() {
        return Err(Error::Path {
            kind: "output directory",
            path: parent.to_path_buf(),
            reason: "path exists but is not a directory".into(),
        });
    }
    let chromatogram = trace::load(&args.trace)?;
    let reference = reference::load(&args.reference, config.reference.topology)?;
    Ok(Inputs {
        config,
        trace: chromatogram,
        reference,
        output,
    })
}

fn require_regular_file(path: &Path, kind: &'static str) -> Result<()> {
    let metadata = path.metadata().map_err(|source| Error::Read {
        kind,
        path: path.to_path_buf(),
        source,
    })?;
    if !metadata.is_file() || metadata.len() == 0 {
        return Err(Error::Path {
            kind,
            path: path.to_path_buf(),
            reason: "path must be a non-empty regular file".into(),
        });
    }
    Ok(())
}

fn output_path(trace: &Path) -> Result<PathBuf> {
    let stem = trace
        .file_stem()
        .and_then(|value| value.to_str())
        .filter(|value| !value.is_empty())
        .ok_or_else(|| Error::Path {
            kind: "AB1",
            path: trace.to_path_buf(),
            reason: "file stem must be valid non-empty UTF-8".into(),
        })?;
    Ok(PathBuf::from("results").join(format!("{stem}.json")))
}
