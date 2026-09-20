//! Canonical rCRS poly-C geometry for read-local phase measurement.

use crate::error::{Error, Result};
use crate::model::alignment::Orientation;
use crate::model::phase::PhaseTractId;
use crate::model::reference::{Reference, ReferenceTopology};

pub(super) const RCRS_LENGTH: usize = 16_569;
pub(super) const RCRS_SEQUENCE_SHA256: &str =
    "f156ff3f65bbcc80c7ebb9936dceb96b1477b4f8f535c4e1dbe7baea225cbc66";

#[derive(Debug, Clone, Copy)]
pub(super) struct Tract {
    pub(super) id: PhaseTractId,
    pub(super) start_0based: usize,
    pub(super) end_0based_inclusive: usize,
    pub(super) interrupt_0based: usize,
    pub(super) reference_sequence: &'static str,
}

pub(super) const TRACTS: [Tract; 2] = [
    Tract {
        id: PhaseTractId::Hv2,
        start_0based: 302,
        end_0based_inclusive: 314,
        interrupt_0based: 309,
        reference_sequence: "CCCCCCCTCCCCC",
    },
    Tract {
        id: PhaseTractId::Hv1,
        start_0based: 16_183,
        end_0based_inclusive: 16_192,
        interrupt_0based: 16_188,
        reference_sequence: "CCCCCTCCCC",
    },
];

pub(super) fn supported_reference(reference: &Reference) -> Result<bool> {
    if reference.topology != ReferenceTopology::Circular
        || reference.len() != RCRS_LENGTH
        || reference.sequence_sha256 != RCRS_SEQUENCE_SHA256
    {
        return Ok(false);
    }

    for tract in TRACTS {
        let actual = reference
            .sequence
            .get(tract.start_0based..=tract.end_0based_inclusive)
            .ok_or_else(|| {
                Error::Phase(format!(
                    "{} tract is outside canonical rCRS bounds",
                    tract.id.label()
                ))
            })?;
        if actual != tract.reference_sequence {
            return Err(Error::Phase(format!(
                "{} tract sequence differs from canonical rCRS",
                tract.id.label()
            )));
        }
    }
    Ok(true)
}

pub(super) const fn tract_exit(tract: Tract, orientation: Orientation) -> usize {
    match orientation {
        Orientation::Forward => tract.end_0based_inclusive,
        Orientation::Reverse => tract.start_0based,
    }
}

pub(super) fn distance_after(
    tract: Tract,
    orientation: Orientation,
    reference_index_0based: usize,
) -> usize {
    let exit = tract_exit(tract, orientation);
    match orientation {
        Orientation::Forward => {
            (reference_index_0based + RCRS_LENGTH - exit) % RCRS_LENGTH
        }
        Orientation::Reverse => {
            (exit + RCRS_LENGTH - reference_index_0based) % RCRS_LENGTH
        }
    }
}

pub(super) fn contains(tract: Tract, reference_index_0based: usize) -> bool {
    (tract.start_0based..=tract.end_0based_inclusive).contains(&reference_index_0based)
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn forward_hv1_distance_wraps_across_rcrs_origin() {
        let hv1 = TRACTS[1];
        assert_eq!(
            distance_after(hv1, Orientation::Forward, 16_193),
            1
        );
        assert_eq!(
            distance_after(hv1, Orientation::Forward, 16_568),
            376
        );
        assert_eq!(distance_after(hv1, Orientation::Forward, 0), 377);
        assert_eq!(distance_after(hv1, Orientation::Forward, 252), 629);
    }

    #[test]
    fn reverse_hv2_distance_follows_selected_sequencing_order() {
        let hv2 = TRACTS[0];
        assert_eq!(distance_after(hv2, Orientation::Reverse, 301), 1);
        assert_eq!(distance_after(hv2, Orientation::Reverse, 0), 302);
        assert_eq!(
            distance_after(hv2, Orientation::Reverse, 16_568),
            303
        );
    }
}
