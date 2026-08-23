//! Projection of variant-associated calls into compact signal records.

use crate::error::{Error, Result};
use crate::model::basecalls::{BaseCall, BaseCalls, ChannelPeak};
use crate::model::coordinate::reference_one_based;
use crate::model::quality::{CallQuality, QualityControlResult};
use crate::model::result::{
    ChannelPeaksResult, PeakResult, VariantCallResult, VariantQualityResult, VariantResult,
};
use crate::model::variant::{Variant, VariantCallMapping};

/// Projects normalized variants and joins their original calls to peaks and quality.
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
        contig: variant.contig,
        position: variant.position_1based,
        reference: variant.reference,
        alternate: variant.alternate,
        kind: variant.kind,
        classification: variant.classification,
        normalization: variant.normalization,
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
        peaks: channel_peaks(call),
        quality: quality_result(score),
    })
}

fn channel_peaks(call: &BaseCall) -> ChannelPeaksResult {
    ChannelPeaksResult {
        a: peak_result(call.peaks[0]),
        c: peak_result(call.peaks[1]),
        g: peak_result(call.peaks[2]),
        t: peak_result(call.peaks[3]),
    }
}

const fn peak_result(peak: ChannelPeak) -> PeakResult {
    PeakResult {
        height: peak.height,
        position: peak.position_0based,
        source: peak.source,
    }
}

const fn quality_result(quality: &CallQuality) -> VariantQualityResult {
    VariantQualityResult {
        relative_score: quality.relative_quality_score,
        penalty: quality.penalty,
        phred_calibrated: quality.phred_calibrated,
        vendor_score: quality.vendor_quality,
        vendor_score_applies: quality.vendor_quality_applies,
    }
}
