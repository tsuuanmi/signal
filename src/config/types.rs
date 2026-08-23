//! Typed and validated configuration records.

use std::path::PathBuf;

use serde::Deserialize;

use crate::config::defaults::MAX_INDEL_LENGTH;
use crate::error::{Error, Result};
use crate::model::reference::ReferenceTopology;

/// Complete effective configuration and source identity.
#[derive(Debug, Clone)]
pub struct Config {
    pub(crate) reference: ReferenceConfig,
    pub(crate) basecalling: BasecallingConfig,
    pub(crate) quality_control: QualityControlConfig,
    pub(crate) alignment: AlignmentConfig,
    pub(crate) variant_calling: VariantCallingConfig,
    pub(crate) source_path: PathBuf,
    pub(crate) source_sha256: String,
}

/// Reference interpretation settings.
#[derive(Debug, Clone)]
pub struct ReferenceConfig {
    pub(crate) topology: ReferenceTopology,
}

/// Signal re-calling settings.
#[derive(Debug, Clone)]
pub struct BasecallingConfig {
    pub(crate) secondary_peak_ratio: f64,
}

/// Relative score and trimming settings.
#[derive(Debug, Clone)]
pub struct QualityControlConfig {
    pub(crate) trim_window_size: usize,
    pub(crate) best_section_fraction: f64,
    pub(crate) max_relative_quality_score: u8,
    pub(crate) trim_stringency: f64,
    pub(crate) minimum_retained_bases: usize,
}

/// Pairwise alignment settings.
#[derive(Debug, Clone)]
pub struct AlignmentConfig {
    pub(crate) match_score: i32,
    pub(crate) mismatch_score: i32,
    pub(crate) ambiguous_score: i32,
    pub(crate) gap_open_score: i32,
    pub(crate) gap_extension_score: i32,
    pub(crate) minimum_callable_bases: usize,
    pub(crate) minimum_identity: f64,
}

/// Primary-difference calling settings.
#[derive(Debug, Clone)]
pub struct VariantCallingConfig {
    pub(crate) max_indel_length: usize,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct RawConfig {
    schema_version: u32,
    reference: RawReferenceConfig,
    basecalling: RawBasecallingConfig,
    quality_control: RawQualityControlConfig,
    alignment: RawAlignmentConfig,
    variant_calling: RawVariantCallingConfig,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct RawReferenceConfig {
    topology: ReferenceTopology,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct RawBasecallingConfig {
    secondary_peak_ratio: f64,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct RawQualityControlConfig {
    trim_window_size: usize,
    best_section_fraction: f64,
    max_relative_quality_score: u8,
    trim_stringency: f64,
    minimum_retained_bases: usize,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct RawAlignmentConfig {
    match_score: i32,
    mismatch_score: i32,
    ambiguous_score: i32,
    gap_open_score: i32,
    gap_extension_score: i32,
    minimum_callable_bases: usize,
    minimum_identity: f64,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct RawVariantCallingConfig {
    max_indel_length: usize,
}

impl RawConfig {
    pub(super) fn validate(self, source_path: PathBuf, source_sha256: String) -> Result<Config> {
        if self.schema_version != 1 {
            return Err(Error::Config(format!(
                "unsupported schema_version {}; expected 1",
                self.schema_version
            )));
        }
        require_fraction(
            "basecalling.secondary_peak_ratio",
            self.basecalling.secondary_peak_ratio,
        )?;
        if self.quality_control.trim_window_size == 0 {
            return Err(Error::Config(
                "quality_control.trim_window_size must be positive".into(),
            ));
        }
        require_fraction(
            "quality_control.best_section_fraction",
            self.quality_control.best_section_fraction,
        )?;
        if self.quality_control.max_relative_quality_score == 0 {
            return Err(Error::Config(
                "quality_control.max_relative_quality_score must be positive".into(),
            ));
        }
        require_finite_range(
            "quality_control.trim_stringency",
            self.quality_control.trim_stringency,
            0.0,
            9.0,
        )?;
        if self.quality_control.minimum_retained_bases == 0 {
            return Err(Error::Config(
                "quality_control.minimum_retained_bases must be positive".into(),
            ));
        }
        if self.alignment.match_score <= 0 {
            return Err(Error::Config(
                "alignment.match_score must be positive".into(),
            ));
        }
        if self.alignment.mismatch_score >= 0
            || self.alignment.gap_open_score >= 0
            || self.alignment.gap_extension_score >= 0
        {
            return Err(Error::Config(
                "alignment mismatch and gap scores must be negative".into(),
            ));
        }
        if self.alignment.minimum_callable_bases == 0 {
            return Err(Error::Config(
                "alignment.minimum_callable_bases must be positive".into(),
            ));
        }
        require_fraction(
            "alignment.minimum_identity",
            self.alignment.minimum_identity,
        )?;
        if self.variant_calling.max_indel_length == 0
            || self.variant_calling.max_indel_length > MAX_INDEL_LENGTH
        {
            return Err(Error::Config(format!(
                "variant_calling.max_indel_length must be in 1..={MAX_INDEL_LENGTH}"
            )));
        }
        Ok(Config {
            reference: ReferenceConfig {
                topology: self.reference.topology,
            },
            basecalling: BasecallingConfig {
                secondary_peak_ratio: self.basecalling.secondary_peak_ratio,
            },
            quality_control: QualityControlConfig {
                trim_window_size: self.quality_control.trim_window_size,
                best_section_fraction: self.quality_control.best_section_fraction,
                max_relative_quality_score: self.quality_control.max_relative_quality_score,
                trim_stringency: self.quality_control.trim_stringency,
                minimum_retained_bases: self.quality_control.minimum_retained_bases,
            },
            alignment: AlignmentConfig {
                match_score: self.alignment.match_score,
                mismatch_score: self.alignment.mismatch_score,
                ambiguous_score: self.alignment.ambiguous_score,
                gap_open_score: self.alignment.gap_open_score,
                gap_extension_score: self.alignment.gap_extension_score,
                minimum_callable_bases: self.alignment.minimum_callable_bases,
                minimum_identity: self.alignment.minimum_identity,
            },
            variant_calling: VariantCallingConfig {
                max_indel_length: self.variant_calling.max_indel_length,
            },
            source_path,
            source_sha256,
        })
    }
}

fn require_fraction(name: &str, value: f64) -> Result<()> {
    require_finite_range(name, value, f64::MIN_POSITIVE, 1.0)
}

fn require_finite_range(name: &str, value: f64, minimum: f64, maximum: f64) -> Result<()> {
    if !value.is_finite() || value < minimum || value > maximum {
        return Err(Error::Config(format!(
            "{name} must be finite and in [{minimum}, {maximum}]"
        )));
    }
    Ok(())
}
