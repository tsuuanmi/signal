//! Deterministic aggregation of normalized variant observations across reads.

use std::collections::{BTreeMap, BTreeSet};

use crate::error::{Error, Result};
use crate::model::read_observation::ReadObservation;
use crate::model::sample_evidence::{VariantCallEvidence, VariantEvidence, VariantSupport};
use crate::model::variant::{VariantCallMapping, VariantKind};

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
struct VariantKey {
    position_1based: usize,
    reference: String,
    alternate: String,
    kind: VariantKind,
}

pub(super) fn aggregate(reads: &[&ReadObservation]) -> Result<Vec<VariantEvidence>> {
    let mut variants: BTreeMap<VariantKey, Vec<VariantSupport>> = BTreeMap::new();

    for (read_index, read) in reads.iter().enumerate() {
        let mut seen = BTreeSet::new();
        for observed in &read.variants.observed {
            let variant = &observed.variant;
            let key = VariantKey {
                position_1based: variant.position_1based,
                reference: variant.reference.clone(),
                alternate: variant.alternate.clone(),
                kind: variant.kind,
            };
            if !seen.insert(key.clone()) {
                return Err(Error::Sample(format!(
                    "read {} contains duplicate normalized variant identity",
                    read.input_sha256
                )));
            }
            variants.entry(key).or_default().push(VariantSupport {
                read_index,
                eligible: observed.eligible(),
                exclusion_reasons: observed.exclusion_reasons.clone(),
                calls: variant_calls(read, &variant.calls)?,
            });
        }
    }

    Ok(variants
        .into_iter()
        .map(|(key, support)| VariantEvidence {
            position_1based: key.position_1based,
            reference: key.reference,
            alternate: key.alternate,
            kind: key.kind,
            support,
        })
        .collect())
}

fn variant_calls(
    read: &ReadObservation,
    mappings: &[VariantCallMapping],
) -> Result<Vec<VariantCallEvidence>> {
    mappings
        .iter()
        .map(|mapping| {
            let call = read
                .calls
                .calls
                .get(mapping.call_index_0based)
                .ok_or_else(|| {
                    Error::Sample(format!(
                        "variant references missing call index {}",
                        mapping.call_index_0based
                    ))
                })?;
            if call.index_0based != mapping.call_index_0based {
                return Err(Error::Sample(format!(
                    "variant call index {} does not match base-call record",
                    mapping.call_index_0based
                )));
            }
            let reference_position_1based = mapping
                .reference_position_0based
                .map(|position| {
                    position
                        .checked_add(1)
                        .ok_or_else(|| Error::Sample("reference coordinate overflow".into()))
                })
                .transpose()?;
            Ok(VariantCallEvidence {
                role: mapping.role,
                call_index_0based: mapping.call_index_0based,
                reference_position_1based,
                ploc_0based: call.ploc_0based,
            })
        })
        .collect()
}
