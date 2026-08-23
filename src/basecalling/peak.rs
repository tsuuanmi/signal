//! Base-window construction and channel-local peak selection.

use crate::error::{Error, Result};
use crate::model::basecalls::{ChannelPeak, PeakSource};
use crate::model::nucleotide::Nucleotide;
use crate::model::trace::Chromatogram;

/// Half-open sample window around one PLOC locus.
#[derive(Debug, Clone, Copy)]
pub(crate) struct CallWindow {
    pub(crate) start: usize,
    pub(crate) end: usize,
}

/// Builds symmetric neighboring-midpoint windows.
pub(crate) fn windows(trace: &Chromatogram) -> Result<Vec<CallWindow>> {
    let positions = &trace.base_locations;
    if positions.len() < 2 {
        return Err(Error::Basecalling(
            "at least two PLOC positions are required".into(),
        ));
    }
    let sample_count = trace.sample_count();
    let mut output = Vec::with_capacity(positions.len());
    for index in 0..positions.len() {
        let start = if index == 0 {
            let spacing = positions[1] - positions[0];
            positions[0].saturating_sub(spacing / 2)
        } else {
            midpoint(positions[index - 1], positions[index])?
        };
        let end = if index + 1 == positions.len() {
            let spacing = positions[index] - positions[index - 1];
            positions[index]
                .checked_add(spacing.div_ceil(2))
                .unwrap_or(sample_count)
                .min(sample_count)
        } else {
            midpoint(positions[index], positions[index + 1])?
        };
        if start >= end || end > sample_count || positions[index] < start || positions[index] >= end
        {
            return Err(Error::Basecalling(format!(
                "invalid call window {start}..{end} for PLOC {}",
                positions[index]
            )));
        }
        output.push(CallWindow { start, end });
    }
    Ok(output)
}

/// Finds one positive local peak per channel or samples PLOC explicitly.
pub(crate) fn peaks(trace: &Chromatogram, window: CallWindow, ploc: usize) -> [ChannelPeak; 4] {
    std::array::from_fn(|channel_index| {
        let channel = &trace.channels[channel_index];
        let search_start = window.start.max(1);
        let search_end = window.end.min(channel.len().saturating_sub(1));
        let mut selected = None;
        for position in search_start..search_end {
            let value = channel[position];
            let local = (channel[position - 1] <= value && value > channel[position + 1])
                || (channel[position - 1] < value && value >= channel[position + 1]);
            if local && value > 0 && selected.is_none_or(|(_, best)| value > best) {
                selected = Some((position, value));
            }
        }
        let (position, height, source) = selected.map_or_else(
            || (ploc, channel[ploc], PeakSource::PlocFallback),
            |(position, height)| (position, height, PeakSource::LocalMaximum),
        );
        ChannelPeak {
            base: Nucleotide::ALL[channel_index],
            height,
            position_0based: position,
            source,
        }
    })
}

fn midpoint(left: usize, right: usize) -> Result<usize> {
    left.checked_add((right - left) / 2)
        .ok_or_else(|| Error::Basecalling("call-window midpoint overflow".into()))
}

#[cfg(test)]
mod tests {
    use crate::model::trace::{Chromatogram, VendorEvidence};

    use super::*;

    #[test]
    fn selects_each_channel_independently_and_falls_back_to_ploc() {
        let trace = Chromatogram {
            source_name: "synthetic.ab1".into(),
            source_sha256: String::new(),
            channels: [
                vec![0, 1, 10, 1, 0, 0, 0],
                vec![0, 1, 2, 20, 1, 0, 0],
                vec![0, 0, 1, 2, 30, 1, 0],
                vec![0, 1, 2, 3, 4, 5, 6],
            ],
            base_locations: vec![3, 5],
            vendor: VendorEvidence::default(),
        };
        let selected = peaks(&trace, CallWindow { start: 1, end: 6 }, 3);
        assert_eq!((selected[0].position_0based, selected[0].height), (2, 10));
        assert_eq!((selected[1].position_0based, selected[1].height), (3, 20));
        assert_eq!((selected[2].position_0based, selected[2].height), (4, 30));
        assert_eq!((selected[3].position_0based, selected[3].height), (3, 3));
        assert_eq!(selected[3].source, PeakSource::PlocFallback);
    }
}
