//! Signal-derived call orchestration at validated PLOC loci.

use crate::basecalling::iupac;
use crate::basecalling::peak;
use crate::config::BasecallingConfig;
use crate::error::{Error, Result};
use crate::model::basecalls::{BaseCall, BaseCalls};
use crate::model::trace::Chromatogram;

/// Re-calls every vendor-defined locus from analyzed channel signals.
pub(crate) fn call(trace: &Chromatogram, config: &BasecallingConfig) -> Result<BaseCalls> {
    let windows = peak::windows(trace)?;
    let mut calls = Vec::with_capacity(trace.call_count());
    let mut primary_sequence = String::with_capacity(trace.call_count());

    for (index, (&ploc, window)) in trace.base_locations.iter().zip(windows).enumerate() {
        let peaks = peak::peaks(trace, window, ploc);
        if peaks
            .iter()
            .any(|peak| peak.position_0based < window.start || peak.position_0based >= window.end)
        {
            return Err(Error::Basecalling(format!(
                "selected peak escaped call window {}..{} at call {index}",
                window.start, window.end
            )));
        }
        let mut order = [0_usize, 1, 2, 3];
        order.sort_by(|left, right| {
            peaks[*right]
                .height
                .cmp(&peaks[*left].height)
                .then_with(|| left.cmp(right))
        });
        let top_height = peaks[order[0]].height;
        let tied_top = top_height > 0 && peaks[order[1]].height == top_height;
        let vendor_primary = trace
            .vendor
            .primary
            .as_ref()
            .and_then(|sequence| sequence.as_bytes().get(index))
            .map(|value| char::from(*value));

        let (primary, ambiguity, qualifying_channels) = if top_height <= 0 || tied_top {
            ('N', 'N', Vec::new())
        } else {
            let top_index = order[0];
            let qualifying_channels = order
                .iter()
                .filter(|channel| {
                    peaks[**channel].height > 0
                        && f64::from(peaks[**channel].height) / f64::from(top_height)
                            >= config.secondary_peak_ratio
                })
                .map(|channel| peaks[*channel].base)
                .collect::<Vec<_>>();
            let strongest = peaks[top_index].base.as_char();
            let (primary, ambiguity) = match qualifying_channels.len() {
                1 => (strongest, strongest),
                2 => (strongest, iupac::code(&qualifying_channels)),
                3 => (strongest, 'N'),
                _ => ('N', 'N'),
            };
            (primary, ambiguity, qualifying_channels)
        };

        primary_sequence.push(primary);
        calls.push(BaseCall {
            index_0based: index,
            ploc_0based: ploc,
            window_start_0based: window.start,
            window_end_0based_exclusive: window.end,
            peaks,
            primary,
            ambiguity,
            qualifying_channels,
            vendor_agrees: vendor_primary.map(|vendor| vendor == primary),
        });
    }

    Ok(BaseCalls {
        calls,
        primary_sequence,
    })
}

#[cfg(test)]
mod tests {
    use crate::model::trace::{Chromatogram, VendorEvidence};

    use super::*;

    fn trace(channels: [Vec<i32>; 4]) -> Chromatogram {
        Chromatogram {
            source_name: "synthetic.ab1".into(),
            source_sha256: String::new(),
            channels,
            base_locations: vec![2, 6],
            vendor: VendorEvidence::default(),
        }
    }

    #[test]
    fn calls_unambiguous_strongest_channel() -> Result<()> {
        let chromatogram = trace([
            vec![0, 1, 20, 1, 0, 1, 20, 1],
            vec![0; 8],
            vec![0; 8],
            vec![0; 8],
        ]);
        let calls = call(
            &chromatogram,
            &BasecallingConfig {
                secondary_peak_ratio: 0.33,
            },
        )?;
        assert_eq!(calls.primary_sequence, "AA");
        assert_eq!(
            calls
                .calls
                .iter()
                .map(|call| call.ambiguity)
                .collect::<String>(),
            "AA"
        );
        Ok(())
    }

    #[test]
    fn exact_strongest_tie_is_unresolved() -> Result<()> {
        let chromatogram = trace([
            vec![0, 1, 20, 1, 0, 1, 20, 1],
            vec![0, 1, 20, 1, 0, 1, 20, 1],
            vec![0; 8],
            vec![0; 8],
        ]);
        let calls = call(
            &chromatogram,
            &BasecallingConfig {
                secondary_peak_ratio: 0.33,
            },
        )?;
        assert_eq!(calls.primary_sequence, "NN");
        Ok(())
    }

    #[test]
    fn three_qualifying_channels_keep_primary_but_not_ambiguity() -> Result<()> {
        let chromatogram = trace([
            vec![0, 1, 100, 1, 0, 1, 100, 1],
            vec![0, 1, 50, 1, 0, 1, 50, 1],
            vec![0, 1, 40, 1, 0, 1, 40, 1],
            vec![0; 8],
        ]);
        let calls = call(
            &chromatogram,
            &BasecallingConfig {
                secondary_peak_ratio: 0.33,
            },
        )?;
        assert_eq!(calls.primary_sequence, "AA");
        assert_eq!(
            calls
                .calls
                .iter()
                .map(|call| call.ambiguity)
                .collect::<String>(),
            "NN"
        );
        Ok(())
    }

    #[test]
    fn four_qualifying_channels_are_fully_unresolved() -> Result<()> {
        let chromatogram = trace([
            vec![0, 1, 100, 1, 0, 1, 100, 1],
            vec![0, 1, 80, 1, 0, 1, 80, 1],
            vec![0, 1, 60, 1, 0, 1, 60, 1],
            vec![0, 1, 40, 1, 0, 1, 40, 1],
        ]);
        let calls = call(
            &chromatogram,
            &BasecallingConfig {
                secondary_peak_ratio: 0.33,
            },
        )?;
        assert_eq!(calls.primary_sequence, "NN");
        assert_eq!(
            calls
                .calls
                .iter()
                .map(|call| call.ambiguity)
                .collect::<String>(),
            "NN"
        );
        assert!(
            calls
                .calls
                .iter()
                .all(|call| call.qualifying_channels.len() == 4)
        );
        Ok(())
    }
}
