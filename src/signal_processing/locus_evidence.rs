//! Basecall-independent signal evidence at each PLOC-defined locus.

use crate::config::SignalProcessingConfig;
use crate::error::{Error, Result};
use crate::locus::{self, LocusWindow};
use crate::model::locus_evidence::{EvidenceProfile, LocusEvidence};
use crate::model::signal::SignalWindow;
use crate::model::trace::Chromatogram;

use super::statistics;

/// Calculates one immutable signal-evidence record per vendor-defined locus.
///
/// Event refinement and profile construction use analyzed channel evidence
/// directly. They do not consume primary calls, ambiguity codes, selected
/// basecall peaks, or qualifying-channel membership.
pub(super) fn calculate(
    trace: &Chromatogram,
    windows: &[SignalWindow],
    config: &SignalProcessingConfig,
) -> Result<Vec<LocusEvidence>> {
    let locus_count = trace.call_count();
    if locus_count < config.window_size_bases {
        return Err(Error::SignalProcessing(format!(
            "{locus_count} loci are fewer than window_size_bases {}",
            config.window_size_bases
        )));
    }
    let expected_window_count = locus_count - config.window_size_bases + 1;
    if windows.len() != expected_window_count {
        return Err(Error::SignalProcessing(format!(
            "expected {expected_window_count} rolling windows for {locus_count} loci, found {}",
            windows.len()
        )));
    }

    let locus_windows = locus::windows(trace).map_err(Error::SignalProcessing)?;
    if locus_windows.len() != locus_count {
        return Err(Error::SignalProcessing(format!(
            "expected {locus_count} locus windows, found {}",
            locus_windows.len()
        )));
    }

    let mut evidence = Vec::with_capacity(locus_count);
    for (locus_index, (&ploc, &locus_window)) in trace
        .base_locations
        .iter()
        .zip(locus_windows.iter())
        .enumerate()
    {
        let context_start = context_start(locus_index, locus_count, config.window_size_bases);
        let context = windows.get(context_start).ok_or_else(|| {
            Error::SignalProcessing(format!(
                "missing rolling context {context_start} for locus {locus_index}"
            ))
        })?;
        validate_context(
            context,
            context_start,
            locus_index,
            trace.sample_count(),
            config,
        )?;

        let (channel_baselines, channel_noise_sigmas) = local_statistics(trace, context)?;
        let event_position = select_event_position(trace, locus_window, ploc, channel_baselines)?;
        let channel_heights =
            std::array::from_fn(|channel| trace.channels[channel][event_position]);
        let corrected_amplitudes = std::array::from_fn(|channel| {
            statistics::corrected_amplitude(channel_heights[channel], channel_baselines[channel])
        });
        let snrs = std::array::from_fn(|channel| {
            statistics::round_metric(statistics::snr(
                corrected_amplitudes[channel],
                channel_noise_sigmas[channel],
            ))
        });

        evidence.push(LocusEvidence {
            call_index_0based: locus_index,
            ploc_0based: ploc,
            window_start_0based: locus_window.start,
            window_end_0based_exclusive: locus_window.end,
            context_call_start_0based: context.call_start_0based,
            context_call_end_0based_exclusive: context.call_end_0based_exclusive,
            context_sample_start_0based: context.sample_start_0based,
            context_sample_end_0based_exclusive: context.sample_end_0based_exclusive,
            event_position_0based: event_position,
            channel_heights,
            channel_baselines,
            channel_noise_sigmas,
            corrected_amplitudes,
            snrs,
            profile: EvidenceProfile::from_corrected_amplitudes(corrected_amplitudes),
        });
    }
    Ok(evidence)
}

fn validate_context(
    context: &SignalWindow,
    expected_start: usize,
    locus_index: usize,
    sample_count: usize,
    config: &SignalProcessingConfig,
) -> Result<()> {
    if context.call_start_0based != expected_start
        || context.call_end_0based_exclusive != expected_start + config.window_size_bases
        || context.sample_start_0based >= context.sample_end_0based_exclusive
        || context.sample_end_0based_exclusive > sample_count
    {
        return Err(Error::SignalProcessing(format!(
            "invalid rolling context for locus {locus_index}"
        )));
    }
    Ok(())
}

fn local_statistics(trace: &Chromatogram, context: &SignalWindow) -> Result<([f64; 4], [f64; 4])> {
    let mut baselines = [0.0; 4];
    let mut noise_sigmas = [0.0; 4];
    for channel in 0..4 {
        let samples = &trace.channels[channel]
            [context.sample_start_0based..context.sample_end_0based_exclusive];
        let local = statistics::estimate(samples)?;
        baselines[channel] = local.baseline;
        noise_sigmas[channel] = local.noise_sigma;
    }
    Ok((baselines, noise_sigmas))
}

/// Refines the event sample without consulting a basecall verdict.
///
/// The selected sample maximizes total non-negative baseline-corrected A/C/G/T
/// amplitude within the PLOC window. Equal evidence prefers the sample nearest
/// PLOC, then the lower sample coordinate.
fn select_event_position(
    trace: &Chromatogram,
    window: LocusWindow,
    ploc: usize,
    baselines: [f64; 4],
) -> Result<usize> {
    let mut best: Option<(usize, f64)> = None;
    for position in window.start..window.end {
        let total = (0..4)
            .map(|channel| {
                statistics::corrected_amplitude(
                    trace.channels[channel][position],
                    baselines[channel],
                )
            })
            .sum::<f64>();
        let replace = best.is_none_or(|(best_position, best_total)| {
            total > best_total
                || (total == best_total
                    && (position.abs_diff(ploc), position)
                        < (best_position.abs_diff(ploc), best_position))
        });
        if replace {
            best = Some((position, total));
        }
    }
    best.map(|(position, _)| position).ok_or_else(|| {
        Error::SignalProcessing(format!(
            "empty locus window {}..{} at PLOC {ploc}",
            window.start, window.end
        ))
    })
}

fn context_start(locus_index: usize, locus_count: usize, window_size_bases: usize) -> usize {
    let left_context = (window_size_bases - 1) / 2;
    locus_index
        .saturating_sub(left_context)
        .min(locus_count - window_size_bases)
}

#[cfg(test)]
mod tests {
    use crate::config::SignalProcessingConfig;
    use crate::model::basecalls::{BaseCall, BaseCalls, ChannelPeak, PeakSource};
    use crate::model::nucleotide::Nucleotide;
    use crate::model::trace::{Chromatogram, VendorEvidence};

    use super::*;

    fn config(window_size_bases: usize) -> SignalProcessingConfig {
        SignalProcessingConfig {
            window_size_bases,
            minimum_primary_snr: 3.0,
            minimum_noisy_windows: 2,
        }
    }

    fn input() -> (Chromatogram, BaseCalls) {
        let mut channels = std::array::from_fn(|_| vec![0; 12]);
        for (index, position) in [1_usize, 3, 5, 7, 9].into_iter().enumerate() {
            let channel = index % 4;
            channels[channel][position] = 100;
        }
        let calls = (0..5)
            .map(|index| {
                let ploc = 1 + index * 2;
                BaseCall {
                    index_0based: index,
                    ploc_0based: ploc,
                    window_start_0based: ploc.saturating_sub(1),
                    window_end_0based_exclusive: (ploc + 1).min(12),
                    peaks: std::array::from_fn(|channel| ChannelPeak {
                        base: Nucleotide::ALL[channel],
                        height: channels[channel][ploc],
                        position_0based: ploc,
                        source: PeakSource::LocalMaximum,
                    }),
                    primary_peak_evidence: None,
                    primary: 'N',
                    ambiguity: 'N',
                    qualifying_channels: Vec::new(),
                    vendor_agrees: None,
                }
            })
            .collect::<Vec<_>>();
        (
            Chromatogram {
                source_name: "synthetic.ab1".into(),
                source_sha256: String::new(),
                channels,
                base_locations: vec![1, 3, 5, 7, 9],
                vendor: VendorEvidence::default(),
            },
            BaseCalls {
                primary_sequence: "NNNNN".into(),
                calls,
            },
        )
    }

    fn evidence() -> Result<Vec<LocusEvidence>> {
        let (trace, calls) = input();
        let config = config(5);
        let windows = super::super::features::calculate(&trace, &calls, &config)?;
        calculate(&trace, &windows, &config)
    }

    #[test]
    fn selects_centered_and_edge_contexts_deterministically() {
        assert_eq!(
            (0..10)
                .map(|index| context_start(index, 10, 5))
                .collect::<Vec<_>>(),
            vec![0, 0, 0, 1, 2, 3, 4, 5, 5, 5]
        );
        assert_eq!(
            (0..10)
                .map(|index| context_start(index, 10, 6))
                .collect::<Vec<_>>(),
            vec![0, 0, 0, 1, 2, 3, 4, 4, 4, 4]
        );
    }

    #[test]
    fn produces_profile_without_a_primary_basecall() -> Result<()> {
        let evidence = evidence()?;
        assert_eq!(evidence.len(), 5);
        let locus = &evidence[2];
        assert_eq!(locus.call_index_0based, 2);
        assert_eq!(locus.ploc_0based, 5);
        assert_eq!(locus.event_position_0based, 5);
        assert_eq!(locus.channel_heights, [0, 0, 100, 0]);
        assert_eq!(locus.corrected_amplitudes, [0.0, 0.0, 100.0, 0.0]);
        assert_eq!(locus.snrs, [0.0, 0.0, 100.0, 0.0]);
        assert_eq!(
            locus.profile.as_ref().map(|profile| profile.weights),
            Some([0.0, 0.0, 1.0, 0.0])
        );
        Ok(())
    }

    #[test]
    fn profile_retains_mixed_channel_mass_independent_of_threshold_membership() -> Result<()> {
        let (mut trace, calls) = input();
        trace.channels[1][5] = 40;
        let config = config(5);
        let windows = super::super::features::calculate(&trace, &calls, &config)?;
        let evidence = calculate(&trace, &windows, &config)?;
        let profile = evidence[2]
            .profile
            .as_ref()
            .ok_or_else(|| Error::SignalProcessing("missing profile".into()))?;
        assert_eq!(evidence[2].event_position_0based, 5);
        assert_eq!(evidence[2].corrected_amplitudes, [0.0, 40.0, 100.0, 0.0]);
        assert_eq!(profile.weights, [0.0, 2.0 / 7.0, 5.0 / 7.0, 0.0]);
        Ok(())
    }

    #[test]
    fn event_refinement_prefers_total_evidence_then_ploc_proximity() -> Result<()> {
        let (mut trace, calls) = input();
        trace.channels[0][4] = 70;
        trace.channels[1][4] = 70;
        trace.channels[2][5] = 120;
        let config = config(5);
        let windows = super::super::features::calculate(&trace, &calls, &config)?;
        let evidence = calculate(&trace, &windows, &config)?;
        assert_eq!(evidence[2].event_position_0based, 4);

        trace.channels[0][6] = 70;
        trace.channels[1][6] = 70;
        let windows = super::super::features::calculate(&trace, &calls, &config)?;
        let evidence = calculate(&trace, &windows, &config)?;
        assert_eq!(evidence[2].event_position_0based, 4);
        Ok(())
    }

    #[test]
    fn zero_corrected_signal_has_no_profile() -> Result<()> {
        let (mut trace, calls) = input();
        for channel in &mut trace.channels {
            channel.fill(0);
        }
        let config = config(5);
        let windows = super::super::features::calculate(&trace, &calls, &config)?;
        let evidence = calculate(&trace, &windows, &config)?;
        assert!(evidence.iter().all(|locus| locus.profile.is_none()));
        Ok(())
    }
}
