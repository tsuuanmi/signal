//! Projection of variant-associated calls into concise signal records.

use crate::error::{Error, Result};
use crate::model::basecalls::BaseCalls;
use crate::model::coordinate::reference_one_based;
use crate::model::quality::QualityControlResult;
use crate::model::result::{VariantCallResult, VariantResult};
use crate::model::variant::{Variant, VariantCallMapping, VariantCallRole};

/// Projects normalized variants and joins their original calls to essential evidence.
pub(super) fn project(
    variants: Vec<Variant>,
    calls: &BaseCalls,
    quality: &QualityControlResult,
) -> Result<Vec<VariantResult>> {
    variants
        .into_iter()
        .map(|variant| project_variant(variant, calls, quality))
        .collect()
}

fn project_variant(
    variant: Variant,
    calls: &BaseCalls,
    quality: &QualityControlResult,
) -> Result<VariantResult> {
    let projected_calls = variant
        .calls
        .into_iter()
        .map(|mapping| project_call(mapping, calls, quality))
        .collect::<Result<Vec<_>>>()?;
    Ok(VariantResult {
        position: variant.position_1based,
        reference: variant.reference,
        alternate: variant.alternate,
        kind: variant.kind,
        calls: projected_calls,
    })
}

fn project_call(
    mapping: VariantCallMapping,
    calls: &BaseCalls,
    quality: &QualityControlResult,
) -> Result<VariantCallResult> {
    let index = mapping.call_index_0based;
    let call = calls
        .calls
        .get(index)
        .ok_or_else(|| Error::Report(format!("variant references missing call index {index}")))?;
    let score = quality.per_call.get(index).ok_or_else(|| {
        Error::Report(format!("variant references missing quality index {index}"))
    })?;
    if call.index_0based != index || score.index_0based != index {
        return Err(Error::Report(format!(
            "variant call index {index} does not match call/quality records"
        )));
    }
    let supporting = mapping.role == VariantCallRole::Supporting;
    Ok(VariantCallResult {
        role: mapping.role,
        index,
        position: mapping
            .reference_position_0based
            .map(reference_one_based)
            .transpose()?,
        ploc: call.ploc_0based,
        primary: call.primary,
        ambiguity: call.ambiguity,
        maximum_peak_height: supporting.then(|| {
            call.peaks
                .iter()
                .map(|peak| peak.height)
                .max()
                .unwrap_or_default()
        }),
        relative_quality: supporting.then_some(score.relative_quality_score),
    })
}
