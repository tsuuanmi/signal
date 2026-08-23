//! Minimal linear-left and circular-canonical indel representation.

use crate::error::{Error, Result};
use crate::model::coordinate::reference_one_based;
use crate::model::reference::{Reference, ReferenceTopology};
use crate::model::variant::{Variant, VariantCallMapping, VariantKind};
use crate::variant_calling::mapping;

pub(crate) fn snv(
    reference: &Reference,
    position: usize,
    alternate: char,
    calls: Vec<VariantCallMapping>,
) -> Result<Variant> {
    mapping::validate_snv(&calls, position)?;
    let reference_base = reference
        .sequence
        .as_bytes()
        .get(position)
        .copied()
        .ok_or_else(|| Error::Variant("SNV reference position is out of bounds".into()))?;
    validated(
        reference,
        Variant {
            contig: reference.name.clone(),
            position_1based: reference_one_based(position)?,
            reference: char::from(reference_base).to_string(),
            alternate: alternate.to_string(),
            kind: VariantKind::Snv,
            classification: "primary_sequence_difference",
            normalization: match reference.topology {
                ReferenceTopology::Linear => "linear_left",
                ReferenceTopology::Circular => "circular_canonical",
            },
            calls,
        },
    )
}

pub(crate) fn insertion(
    reference: &Reference,
    previous_reference: Option<usize>,
    next_reference: Option<usize>,
    inserted: String,
    calls: Vec<VariantCallMapping>,
) -> Result<Variant> {
    if inserted.is_empty() {
        return Err(Error::Variant("insertion allele is empty".into()));
    }
    mapping::validate_insertion(&calls)?;
    let anchor = observed_anchor(reference, previous_reference, next_reference)?;
    match reference.topology {
        ReferenceTopology::Linear => {
            if let Some(anchor) = anchor {
                let (anchor, inserted) = shift_linear(reference, anchor, inserted)?;
                build_insertion(reference, anchor, &inserted, calls, "linear_left")
            } else {
                let right_anchor = next_reference.ok_or_else(|| {
                    Error::Variant("leading insertion lacks a right anchor".into())
                })?;
                let base = reference_base(reference, right_anchor)?;
                validated(
                    reference,
                    Variant {
                        contig: reference.name.clone(),
                        position_1based: reference_one_based(right_anchor)?,
                        reference: base.to_string(),
                        alternate: format!("{inserted}{base}"),
                        kind: VariantKind::Ins,
                        classification: "primary_sequence_difference",
                        normalization: "linear_left",
                        calls,
                    },
                )
            }
        }
        ReferenceTopology::Circular => {
            let anchor = anchor.ok_or_else(|| {
                Error::Variant("circular insertion lacks an adjacent reference base".into())
            })?;
            let (anchor, inserted) = canonical_circular(reference, anchor, inserted)?;
            build_insertion(reference, anchor, &inserted, calls, "circular_canonical")
        }
    }
}

pub(crate) fn deletion(
    reference: &Reference,
    previous_reference: Option<usize>,
    first_deleted_reference: usize,
    next_reference: Option<usize>,
    deleted: String,
    calls: Vec<VariantCallMapping>,
) -> Result<Variant> {
    if deleted.is_empty() {
        return Err(Error::Variant("deletion allele is empty".into()));
    }
    mapping::validate_deletion(&calls)?;
    let anchor = observed_anchor(reference, previous_reference, Some(first_deleted_reference))?;
    match reference.topology {
        ReferenceTopology::Linear => {
            if let Some(anchor) = anchor {
                let (anchor, deleted) = shift_linear(reference, anchor, deleted)?;
                build_deletion(reference, anchor, &deleted, calls, "linear_left")
            } else {
                let right_anchor = next_reference.ok_or_else(|| {
                    Error::Variant("leading deletion lacks a right anchor".into())
                })?;
                let base = reference_base(reference, right_anchor)?;
                validated(
                    reference,
                    Variant {
                        contig: reference.name.clone(),
                        position_1based: 1,
                        reference: format!("{deleted}{base}"),
                        alternate: base.to_string(),
                        kind: VariantKind::Del,
                        classification: "primary_sequence_difference",
                        normalization: "linear_left",
                        calls,
                    },
                )
            }
        }
        ReferenceTopology::Circular => {
            let anchor = anchor.ok_or_else(|| {
                Error::Variant("circular deletion lacks an adjacent reference base".into())
            })?;
            let (anchor, deleted) = canonical_circular(reference, anchor, deleted)?;
            build_deletion(reference, anchor, &deleted, calls, "circular_canonical")
        }
    }
}

fn observed_anchor(
    reference: &Reference,
    previous_reference: Option<usize>,
    event_reference: Option<usize>,
) -> Result<Option<usize>> {
    if let Some(anchor) = previous_reference {
        reference_base(reference, anchor)?;
        return Ok(Some(anchor));
    }
    let Some(position) = event_reference else {
        return Ok(None);
    };
    reference_base(reference, position)?;
    Ok(match reference.topology {
        ReferenceTopology::Linear => position.checked_sub(1),
        ReferenceTopology::Circular => Some((position + reference.len() - 1) % reference.len()),
    })
}

fn shift_linear(
    reference: &Reference,
    mut anchor: usize,
    mut allele: String,
) -> Result<(usize, String)> {
    while anchor > 0 {
        let anchor_base = reference_base(reference, anchor)?;
        let last = allele
            .pop()
            .ok_or_else(|| Error::Variant("indel allele became empty".into()))?;
        if anchor_base != last {
            allele.push(last);
            break;
        }
        allele.insert(0, last);
        anchor -= 1;
    }
    Ok((anchor, allele))
}

fn canonical_circular(
    reference: &Reference,
    anchor: usize,
    allele: String,
) -> Result<(usize, String)> {
    let mut current_anchor = anchor;
    let mut current_allele = allele;
    let mut full_cycle_best = (current_anchor + 1, current_allele.clone());
    for _ in 0..reference.len() {
        let anchor_base = reference_base(reference, current_anchor)?;
        let last = current_allele
            .pop()
            .ok_or_else(|| Error::Variant("indel allele became empty".into()))?;
        if anchor_base != last {
            current_allele.push(last);
            return Ok((current_anchor, current_allele));
        }
        current_allele.insert(0, last);
        current_anchor = (current_anchor + reference.len() - 1) % reference.len();
        let candidate = (current_anchor + 1, current_allele.clone());
        if candidate < full_cycle_best {
            full_cycle_best = candidate;
        }
    }
    Ok((full_cycle_best.0 - 1, full_cycle_best.1))
}

fn build_insertion(
    reference: &Reference,
    anchor: usize,
    inserted: &str,
    calls: Vec<VariantCallMapping>,
    normalization: &'static str,
) -> Result<Variant> {
    let base = reference_base(reference, anchor)?;
    validated(
        reference,
        Variant {
            contig: reference.name.clone(),
            position_1based: reference_one_based(anchor)?,
            reference: base.to_string(),
            alternate: format!("{base}{inserted}"),
            kind: VariantKind::Ins,
            classification: "primary_sequence_difference",
            normalization,
            calls,
        },
    )
}

fn build_deletion(
    reference: &Reference,
    anchor: usize,
    deleted: &str,
    calls: Vec<VariantCallMapping>,
    normalization: &'static str,
) -> Result<Variant> {
    let base = reference_base(reference, anchor)?;
    validated(
        reference,
        Variant {
            contig: reference.name.clone(),
            position_1based: reference_one_based(anchor)?,
            reference: format!("{base}{deleted}"),
            alternate: base.to_string(),
            kind: VariantKind::Del,
            classification: "primary_sequence_difference",
            normalization,
            calls,
        },
    )
}

fn validated(reference: &Reference, variant: Variant) -> Result<Variant> {
    let start = variant
        .position_1based
        .checked_sub(1)
        .ok_or_else(|| Error::Variant("variant position must be one-based".into()))?;
    for (offset, observed) in variant.reference.bytes().enumerate() {
        let unwrapped = start
            .checked_add(offset)
            .ok_or_else(|| Error::Variant("variant reference span overflow".into()))?;
        let position = match reference.topology {
            ReferenceTopology::Linear => unwrapped,
            ReferenceTopology::Circular => unwrapped % reference.len(),
        };
        let expected = reference
            .sequence
            .as_bytes()
            .get(position)
            .copied()
            .ok_or_else(|| Error::Variant("variant reference span is out of bounds".into()))?;
        if observed != expected {
            return Err(Error::Variant(format!(
                "variant reference allele disagrees with the supplied reference at position {}",
                position + 1
            )));
        }
    }
    Ok(variant)
}

fn reference_base(reference: &Reference, position: usize) -> Result<char> {
    reference
        .sequence
        .as_bytes()
        .get(position)
        .copied()
        .map(char::from)
        .ok_or_else(|| Error::Variant("indel anchor is outside the reference".into()))
}

#[cfg(test)]
mod tests {
    use crate::model::variant::VariantCallRole;

    use super::*;

    fn reference(sequence: &str, topology: ReferenceTopology) -> Reference {
        Reference {
            name: "ref".into(),
            sequence: sequence.into(),
            topology,
            sequence_sha256: String::new(),
        }
    }

    fn inserted_calls() -> Vec<VariantCallMapping> {
        vec![VariantCallMapping {
            role: VariantCallRole::Supporting,
            call_index_0based: 0,
            reference_position_0based: None,
        }]
    }

    fn deletion_flanks() -> Vec<VariantCallMapping> {
        vec![VariantCallMapping {
            role: VariantCallRole::Flanking,
            call_index_0based: 0,
            reference_position_0based: Some(0),
        }]
    }

    #[test]
    fn left_normalizes_homopolymer_insertion() -> Result<()> {
        let variant = insertion(
            &reference("CAAAAG", ReferenceTopology::Linear),
            Some(4),
            Some(5),
            "A".into(),
            inserted_calls(),
        )?;
        assert_eq!(variant.position_1based, 1);
        assert_eq!(variant.reference, "C");
        assert_eq!(variant.alternate, "CA");
        Ok(())
    }

    #[test]
    fn normalization_preserves_observed_call_positions() -> Result<()> {
        let calls = vec![
            VariantCallMapping {
                role: VariantCallRole::Flanking,
                call_index_0based: 4,
                reference_position_0based: Some(4),
            },
            VariantCallMapping {
                role: VariantCallRole::Flanking,
                call_index_0based: 5,
                reference_position_0based: Some(6),
            },
        ];
        let variant = deletion(
            &reference("CAAAAAG", ReferenceTopology::Linear),
            Some(4),
            5,
            Some(6),
            "A".into(),
            calls.clone(),
        )?;
        assert_eq!(variant.position_1based, 1);
        assert_eq!(variant.calls, calls);
        Ok(())
    }

    #[test]
    fn circular_normalization_is_bounded() -> Result<()> {
        let variant = deletion(
            &reference("AAAA", ReferenceTopology::Circular),
            Some(3),
            0,
            Some(1),
            "A".into(),
            deletion_flanks(),
        )?;
        assert_eq!(variant.position_1based, 1);
        assert_eq!(variant.reference, "AA");
        assert_eq!(variant.alternate, "A");
        Ok(())
    }

    #[test]
    fn circular_repeat_normalization_is_anchor_independent() -> Result<()> {
        let reference = reference("AACAA", ReferenceTopology::Circular);
        let after_zero = deletion(
            &reference,
            Some(0),
            1,
            Some(2),
            "A".into(),
            deletion_flanks(),
        )?;
        let after_four = deletion(
            &reference,
            Some(4),
            0,
            Some(1),
            "A".into(),
            deletion_flanks(),
        )?;
        assert_eq!(after_zero.position_1based, 3);
        assert_eq!(after_zero.reference, "CA");
        assert_eq!(after_zero.alternate, "C");
        assert_eq!(after_four.position_1based, after_zero.position_1based);
        assert_eq!(after_four.reference, after_zero.reference);
        assert_eq!(after_four.alternate, after_zero.alternate);
        Ok(())
    }

    #[test]
    fn circular_insertion_normalization_is_anchor_independent() -> Result<()> {
        let reference = reference("AACAA", ReferenceTopology::Circular);
        let after_zero = insertion(&reference, Some(0), Some(1), "A".into(), inserted_calls())?;
        let after_four = insertion(&reference, Some(4), Some(0), "A".into(), inserted_calls())?;
        assert_eq!(after_zero.position_1based, 3);
        assert_eq!(after_zero.reference, "C");
        assert_eq!(after_zero.alternate, "CA");
        assert_eq!(after_four.position_1based, after_zero.position_1based);
        assert_eq!(after_four.reference, after_zero.reference);
        assert_eq!(after_four.alternate, after_zero.alternate);
        Ok(())
    }

    #[test]
    fn rejects_reference_alleles_that_disagree_with_the_reference() {
        let result = deletion(
            &reference("TTCG", ReferenceTopology::Linear),
            Some(1),
            2,
            Some(3),
            "A".into(),
            deletion_flanks(),
        );
        assert!(matches!(result, Err(Error::Variant(message)) if message.contains("disagrees")));
    }

    #[test]
    fn derives_internal_linear_predecessor_without_an_aligned_left_flank() -> Result<()> {
        let reference = reference("TTCG", ReferenceTopology::Linear);
        let variant = deletion(&reference, None, 2, Some(3), "C".into(), deletion_flanks())?;
        assert_eq!(variant.position_1based, 2);
        assert_eq!(variant.reference, "TC");
        assert_eq!(variant.alternate, "T");
        Ok(())
    }

    #[test]
    fn derives_non_origin_circular_predecessor_without_an_aligned_left_flank() -> Result<()> {
        let reference = reference("ACGT", ReferenceTopology::Circular);
        let variant = deletion(&reference, None, 2, Some(3), "G".into(), deletion_flanks())?;
        assert_eq!(variant.position_1based, 2);
        assert_eq!(variant.reference, "CG");
        assert_eq!(variant.alternate, "C");
        Ok(())
    }
}
