//! Per-call local signal observations from primary-event evidence.

use crate::config::SignalProcessingConfig;
use crate::error::{Error, Result};
use crate::model::basecalls::BaseCalls;
use crate::model::signal::{CallSignalMetrics, PrimaryEventSignalMetrics, SignalWindow};
use crate::model::trace::Chromatogram;

use super::statistics;

/// Calculates one local signal-metric record per original call.
pub(super) fn calculate(
    trace: &Chromatogram,
    calls: &BaseCalls,
    windows: &[SignalWindow],
    config: &SignalProcessingConfig,
) -> Result<Vec<CallSignalMetrics>> {
    if calls.len() < config.window_size_bases {
        return Err(Error::SignalProcessing(format!(
            "{} calls are fewer than window_size_bases {}",
            calls.len(),
            config.window_size_bases
        )));
    }
    let expected_window_count = calls.len() - config.window_size_bases + 1;
    if windows.len() != expected_window_count {
        return Err(Error::SignalProcessing(format!(
            "expected {expected_window_count} rolling windows for {} calls, found {}",
            calls.len(),
            windows.len()
        )));
    }

    let mut metrics = Vec::with_capacity(calls.len());
    for (call_index, call) in calls.calls.iter().enumerate() {
        let context_start = context_start(call_index, calls.len(), config.window_size_bases);
        let context = windows.get(context_start).ok_or_else(|| {
            Error::SignalProcessing(format!(
                "missing rolling context {context_start} for call {call_index}"
            ))
        })?;
        if context.call_start_0based != context_start
            || context.call_end_0based_exclusive != context_start + config.window_size_bases
            || context.sample_start_0based >= context.sample_end_0based_exclusive
            || context.sample_end_0based_exclusive > trace.sample_count()
        {
            return Err(Error::SignalProcessing(format!(
                "invalid rolling context for call {call_index}"
            )));
        }

        let mut channel_baselines = [0.0; 4];
        let mut channel_noise_sigmas = [0.0; 4];
        for channel in 0..4 {
            let samples = &trace.channels[channel]
                [context.sample_start_0based..context.sample_end_0based_exclusive];
            let statistics = statistics::estimate(samples)?;
            channel_baselines[channel] = statistics.baseline;
            channel_noise_sigmas[channel] = statistics.noise_sigma;
        }
        let primary_event = call.primary_peak_evidence.as_ref().map(|evidence| {
            let corrected_amplitudes = std::array::from_fn(|channel| {
                statistics::corrected_amplitude(
                    evidence.channel_heights[channel],
                    channel_baselines[channel],
                )
            });
            let snrs = std::array::from_fn(|channel| {
                statistics::round_metric(statistics::snr(
                    corrected_amplitudes[channel],
                    channel_noise_sigmas[channel],
                ))
            });
            PrimaryEventSignalMetrics {
                position_0based: evidence.position_0based,
                corrected_amplitudes,
                snrs,
            }
        });
        metrics.push(CallSignalMetrics {
            call_index_0based: call.index_0based,
            context_call_start_0based: context.call_start_0based,
            context_call_end_0based_exclusive: context.call_end_0based_exclusive,
            sample_start_0based: context.sample_start_0based,
            sample_end_0based_exclusive: context.sample_end_0based_exclusive,
            channel_baselines,
            channel_noise_sigmas,
            primary_event,
        });
    }
    Ok(metrics)
}

fn context_start(call_index: usize, call_count: usize, window_size_bases: usize) -> usize {
    let left_context = (window_size_bases - 1) / 2;
    call_index
        .saturating_sub(left_context)
        .min(call_count - window_size_bases)
}

#[cfg(test)]
mod tests {
    use crate::config::SignalProcessingConfig;
    use crate::model::basecalls::{
        BaseCall, BaseCalls, ChannelPeak, PeakSource, PrimaryPeakEvidence,
    };
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

    fn input(
        primary_peak_evidence: Option<PrimaryPeakEvidence>,
        remote_secondary: bool,
    ) -> (Chromatogram, BaseCalls) {
        let mut channels = std::array::from_fn(|_| vec![0; 10]);
        if let Some(evidence) = &primary_peak_evidence {
            for (channel, channel_samples) in channels.iter_mut().enumerate() {
                channel_samples[evidence.position_0based] = evidence.channel_heights[channel];
            }
        }
        if remote_secondary {
            channels[1][5] = 80;
        }
        let calls = (0..5)
            .map(|index| {
                let primary = index == 2;
                BaseCall {
                    index_0based: index,
                    ploc_0based: index * 2,
                    window_start_0based: index * 2,
                    window_end_0based_exclusive: index * 2 + 2,
                    peaks: std::array::from_fn(|channel| ChannelPeak {
                        base: Nucleotide::ALL[channel],
                        height: if primary {
                            if channel == 0 {
                                100
                            } else if channel == 1 && remote_secondary {
                                80
                            } else {
                                primary_peak_evidence
                                    .as_ref()
                                    .map_or(0, |evidence| evidence.channel_heights[channel])
                            }
                        } else {
                            0
                        },
                        position_0based: if primary && channel == 1 && remote_secondary {
                            5
                        } else {
                            index * 2
                        },
                        source: PeakSource::LocalMaximum,
                    }),
                    primary_peak_evidence: if primary {
                        primary_peak_evidence.clone()
                    } else {
                        None
                    },
                    primary: 'A',
                    ambiguity: 'A',
                    qualifying_channels: vec![Nucleotide::A],
                    vendor_agrees: None,
                }
            })
            .collect::<Vec<_>>();
        (
            Chromatogram {
                source_name: "synthetic.ab1".into(),
                source_sha256: String::new(),
                channels,
                base_locations: (0..5).map(|index| index * 2).collect(),
                vendor: VendorEvidence::default(),
            },
            BaseCalls {
                primary_sequence: "AAAAA".into(),
                calls,
            },
        )
    }

    fn metrics(
        primary_peak_evidence: Option<PrimaryPeakEvidence>,
        remote_secondary: bool,
    ) -> Result<Vec<CallSignalMetrics>> {
        let (trace, calls) = input(primary_peak_evidence, remote_secondary);
        let config = config(5);
        let windows = super::super::features::calculate(&trace, &calls, &config)?;
        calculate(&trace, &calls, &windows, &config)
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
    fn records_co_located_corrected_amplitudes_and_snrs() -> Result<()> {
        let metrics = metrics(
            Some(PrimaryPeakEvidence {
                position_0based: 4,
                channel_heights: [100, 40, 3, -7],
            }),
            false,
        )?;
        assert_eq!(metrics.len(), 5);
        assert!(
            metrics
                .iter()
                .enumerate()
                .all(|(index, metric)| metric.call_index_0based == index)
        );
        assert_eq!(
            metrics[2]
                .primary_event
                .as_ref()
                .map(|event| event.position_0based),
            Some(4)
        );
        assert_eq!(
            metrics[2]
                .primary_event
                .as_ref()
                .map(|event| event.corrected_amplitudes),
            Some([100.0, 40.0, 3.0, 0.0])
        );
        assert_eq!(
            metrics[2].primary_event.as_ref().map(|event| event.snrs),
            Some([100.0, 40.0, 3.0, 0.0])
        );
        assert!(metrics.iter().all(|metric| {
            metric.context_call_start_0based <= metric.call_index_0based
                && metric.call_index_0based < metric.context_call_end_0based_exclusive
                && metric.context_call_end_0based_exclusive - metric.context_call_start_0based == 5
                && metric.sample_start_0based < metric.sample_end_0based_exclusive
                && metric
                    .channel_noise_sigmas
                    .iter()
                    .all(|sigma| *sigma >= 1.0)
        }));
        Ok(())
    }

    #[test]
    fn uses_co_located_secondary_not_remote_selected_peak() -> Result<()> {
        let metrics = metrics(
            Some(PrimaryPeakEvidence {
                position_0based: 4,
                channel_heights: [100, 5, 0, 0],
            }),
            true,
        )?;
        assert_eq!(
            metrics[2]
                .primary_event
                .as_ref()
                .map(|event| event.corrected_amplitudes[1]),
            Some(5.0)
        );
        assert_eq!(
            metrics[2].primary_event.as_ref().map(|event| event.snrs[1]),
            Some(5.0)
        );
        Ok(())
    }

    #[test]
    fn retains_context_without_a_primary_event() -> Result<()> {
        let metrics = metrics(None, false)?;
        assert!(metrics[2].primary_event.is_none());
        assert_eq!(metrics[2].channel_baselines, [0.0; 4]);
        assert_eq!(metrics[2].channel_noise_sigmas, [1.0; 4]);
        Ok(())
    }
}
