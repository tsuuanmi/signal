//! Rolling sample-domain baseline, noise, and peak-SNR features.

use crate::config::SignalProcessingConfig;
use crate::error::{Error, Result};
use crate::model::basecalls::BaseCalls;
use crate::model::signal::SignalWindow;
use crate::model::trace::Chromatogram;

const NORMAL_MAD_SCALE: f64 = 0.674_489_75;
const FIRST_DIFFERENCE_SCALE: f64 = std::f64::consts::SQRT_2;
const MINIMUM_NOISE_SIGMA: f64 = 1.0;
const OUTPUT_PRECISION: f64 = 1_000_000.0;

/// Computes one feature record per full-width, stride-one base window.
pub(super) fn calculate(
    trace: &Chromatogram,
    calls: &BaseCalls,
    config: &SignalProcessingConfig,
) -> Result<Vec<SignalWindow>> {
    if calls.len() < config.window_size_bases {
        return Err(Error::SignalProcessing(format!(
            "{} calls are fewer than window_size_bases {}",
            calls.len(),
            config.window_size_bases
        )));
    }

    let mut windows = Vec::with_capacity(calls.len() - config.window_size_bases + 1);
    for call_start in 0..=calls.len() - config.window_size_bases {
        let call_end = call_start + config.window_size_bases;
        let selected = &calls.calls[call_start..call_end];
        let sample_start = selected[0].window_start_0based;
        let sample_end = selected[selected.len() - 1].window_end_0based_exclusive;
        if sample_start >= sample_end || sample_end > trace.sample_count() {
            return Err(Error::SignalProcessing(format!(
                "invalid sample interval {sample_start}..{sample_end} for call window {call_start}..{call_end}"
            )));
        }

        let mut baselines = [0.0; 4];
        let mut noise_sigmas = [0.0; 4];
        for channel in 0..4 {
            let samples = &trace.channels[channel][sample_start..sample_end];
            baselines[channel] = median_i32(samples)?;
            noise_sigmas[channel] = noise_sigma(samples)?;
        }

        let mut minimum_primary_snr = f64::INFINITY;
        let mut maximum_secondary_snr = 0.0_f64;
        for call in selected {
            let mut ranked = [0_usize, 1, 2, 3];
            let corrected = std::array::from_fn::<_, 4, _>(|channel| {
                (f64::from(call.peaks[channel].height) - baselines[channel]).max(0.0)
            });
            ranked.sort_by(|left, right| {
                corrected[*right]
                    .total_cmp(&corrected[*left])
                    .then_with(|| left.cmp(right))
            });
            let primary = ranked[0];
            let secondary = ranked[1];
            minimum_primary_snr =
                minimum_primary_snr.min(corrected[primary] / noise_sigmas[primary]);
            maximum_secondary_snr =
                maximum_secondary_snr.max(corrected[secondary] / noise_sigmas[secondary]);
        }

        let minimum_primary_snr = round_metric(minimum_primary_snr);
        let maximum_secondary_snr = round_metric(maximum_secondary_snr);
        windows.push(SignalWindow {
            call_start_0based: call_start,
            call_end_0based_exclusive: call_end,
            sample_start_0based: sample_start,
            sample_end_0based_exclusive: sample_end,
            minimum_primary_snr,
            maximum_secondary_snr,
            candidate_noisy: minimum_primary_snr < config.minimum_primary_snr,
        });
    }
    Ok(windows)
}

fn median_i32(values: &[i32]) -> Result<f64> {
    if values.is_empty() {
        return Err(Error::SignalProcessing(
            "cannot calculate a median from an empty sample interval".into(),
        ));
    }
    let mut sorted = values.to_vec();
    sorted.sort_unstable();
    Ok(median_sorted_i32(&sorted))
}

fn median_sorted_i32(sorted: &[i32]) -> f64 {
    let middle = sorted.len() / 2;
    if sorted.len() % 2 == 0 {
        (f64::from(sorted[middle - 1]) + f64::from(sorted[middle])) / 2.0
    } else {
        f64::from(sorted[middle])
    }
}

fn noise_sigma(samples: &[i32]) -> Result<f64> {
    if samples.len() < 2 {
        return Err(Error::SignalProcessing(
            "noise estimation requires at least two channel samples".into(),
        ));
    }
    let mut differences = samples
        .windows(2)
        .map(|pair| f64::from(pair[1]) - f64::from(pair[0]))
        .collect::<Vec<_>>();
    differences.sort_by(f64::total_cmp);
    let center = median_sorted_f64(&differences);
    let mut deviations = differences
        .into_iter()
        .map(|difference| (difference - center).abs())
        .collect::<Vec<_>>();
    deviations.sort_by(f64::total_cmp);
    let mad = median_sorted_f64(&deviations);
    Ok((mad / (NORMAL_MAD_SCALE * FIRST_DIFFERENCE_SCALE)).max(MINIMUM_NOISE_SIGMA))
}

fn median_sorted_f64(sorted: &[f64]) -> f64 {
    let middle = sorted.len() / 2;
    if sorted.len() % 2 == 0 {
        (sorted[middle - 1] + sorted[middle]) / 2.0
    } else {
        sorted[middle]
    }
}

fn round_metric(value: f64) -> f64 {
    (value * OUTPUT_PRECISION).round() / OUTPUT_PRECISION
}

#[cfg(test)]
mod tests {
    use crate::model::basecalls::{BaseCall, ChannelPeak, PeakSource};
    use crate::model::nucleotide::Nucleotide;
    use crate::model::trace::VendorEvidence;

    use super::*;

    fn evidence(count: usize) -> (Chromatogram, BaseCalls) {
        let sample_count = count * 4 + 4;
        let mut channels: [Vec<i32>; 4] = std::array::from_fn(|_| vec![0; sample_count]);
        let mut records = Vec::with_capacity(count);
        for index in 0..count {
            let ploc = 2 + index * 4;
            let primary_channel = index % 4;
            let primary = Nucleotide::ALL[primary_channel];
            channels[primary_channel][ploc] = 1_000;
            records.push(BaseCall {
                index_0based: index,
                ploc_0based: ploc,
                window_start_0based: ploc - 2,
                window_end_0based_exclusive: ploc + 2,
                peaks: std::array::from_fn(|channel| ChannelPeak {
                    base: Nucleotide::ALL[channel],
                    height: if channel == primary_channel { 1_000 } else { 0 },
                    position_0based: ploc,
                    source: if channel == primary_channel {
                        PeakSource::LocalMaximum
                    } else {
                        PeakSource::PlocFallback
                    },
                }),
                primary: primary.as_char(),
                ambiguity: primary.as_char(),
                qualifying_channels: vec![primary],
                vendor_agrees: None,
            });
        }
        let sequence = records.iter().map(|call| call.primary).collect::<String>();
        (
            Chromatogram {
                source_name: "synthetic.ab1".into(),
                source_sha256: String::new(),
                channels,
                base_locations: records.iter().map(|call| call.ploc_0based).collect(),
                vendor: VendorEvidence::default(),
            },
            BaseCalls {
                calls: records,
                primary_sequence: sequence,
            },
        )
    }

    #[test]
    fn flat_samples_use_the_quantization_floor() -> Result<()> {
        assert_eq!(noise_sigma(&[4, 4, 4, 4])?, 1.0);
        Ok(())
    }

    #[test]
    fn median_handles_even_and_odd_sample_counts() -> Result<()> {
        assert_eq!(median_i32(&[4, 1, 3])?, 3.0);
        assert_eq!(median_i32(&[4, 1, 3, 2])?, 2.5);
        Ok(())
    }

    #[test]
    fn computes_full_windows_and_keeps_exact_threshold_clean() -> Result<()> {
        let (trace, calls) = evidence(7);
        let windows = calculate(
            &trace,
            &calls,
            &SignalProcessingConfig {
                window_size_bases: 5,
                minimum_primary_snr: 1_000.0,
                minimum_noisy_windows: 2,
            },
        )?;
        assert_eq!(windows.len(), 3);
        assert_eq!(windows[0].call_start_0based, 0);
        assert_eq!(windows[0].call_end_0based_exclusive, 5);
        assert_eq!(windows[0].minimum_primary_snr, 1_000.0);
        assert!(!windows[0].candidate_noisy);
        assert!(
            windows
                .iter()
                .all(|window| window.minimum_primary_snr.is_finite())
        );
        Ok(())
    }

    #[test]
    fn rejects_a_trace_shorter_than_the_configured_window() {
        let (trace, calls) = evidence(4);
        assert!(matches!(
            calculate(
                &trace,
                &calls,
                &SignalProcessingConfig {
                    window_size_bases: 5,
                    minimum_primary_snr: 3.0,
                    minimum_noisy_windows: 2,
                },
            ),
            Err(Error::SignalProcessing(message)) if message.contains("fewer than")
        ));
    }
}
