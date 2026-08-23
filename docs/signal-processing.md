# Observational Signal-Quality Analysis

## Scope

Signal reads the analyzed ABIF `DATA.9`–`DATA.12` arrays in canonical A/C/G/T order. These are instrument-analyzed fluorescence channels, not raw detector channels. The current ABIF boundary does not retain a spectral matrix, mobility model, or raw-channel baseline metadata.

The `signal.windowed_snr/v1` stage is deliberately observational. It calculates rolling windows internally and emits only merged candidate-noisy regions in compact v5; it does not smooth channels, re-call bases, trim internal sequence, change an alignment, or remove a variant.

## Coordinate domains

- **Sample indexes** address A/C/G/T channel values and PLOC positions.
- **Call indexes** address base calls, quality records, and variant mappings.

Both are 0-based. Window and region intervals are half-open. Each base call retains the midpoint-derived sample interval used by peak selection, allowing signal analysis to map a rolling call window to exactly one sample span without reconstructing geometry.

## Method

Configuration chooses `window_size_bases` in `5..=10`, a positive finite `minimum_primary_snr`, and `minimum_noisy_windows` of at least `2`. The default window is 10 bases. Windows have that complete width and stride one; short partial windows are never emitted. A noisy interval is emitted only when a consecutive run contains at least the configured number of candidate-noisy windows.

For each channel in a rolling sample span:

```text
baseline = median(samples)
noise_sigma = max(1, MAD(first_difference(samples)) / (0.67448975 × sqrt(2)))
peak_snr = max(0, selected_peak_height - baseline) / noise_sigma
```

The one-unit floor reflects signed-short quantization and prevents NaN or infinity. Within each call, baseline-corrected selected peaks are ranked deterministically by value and then A/C/G/T order. A window records its minimum primary SNR and maximum secondary SNR internally. Values are rounded to six decimal places before threshold comparison; only each merged region's minimum primary SNR is serialized.

A window is `candidate_noisy` only when its minimum primary SNR is strictly below the configured threshold. Overlapping or adjacent candidate windows are unioned; clean gaps are never filled. Secondary SNR participates only in internal observation and does not make a window noisy because a strong secondary peak may be real mixed signal. Compact v5 omits individual windows and secondary-SNR values.

## Interpretation limits

The SNR is an uncalibrated local feature, not a Phred score or error probability. Fixed thresholds may not transfer across instruments, chemistries, or runs.
Because first differences are measured across the complete span, real peak edges,
broad peaks, and homopolymers can inflate the estimated noise; this v1 metric is
not a detector-background measurement. A merged region is the union of low-SNR
windows, not a per-call noise classification, so it can include calls that were
not individually weak. Candidate-noisy regions therefore have no
variant-eligibility authority in v1.

Phred demonstrates that trace features require empirical calibration before becoming error probabilities: [Ewing et al. 1998](https://doi.org/10.1101/gr.8.3.175) and [Ewing & Green 1998](https://doi.org/10.1101/gr.8.3.186).

## Deferred cleaning

No disabled transform or compatibility branch is included. A later behavior-changing method must preserve the decoded trace and produce a separate processed projection. Candidate methods include peak-preserving Savitzky–Golay smoothing ([Savitzky and Golay 1964](https://doi.org/10.1021/ac60214a047)), asymmetric baseline correction ([Eilers 2003](https://doi.org/10.1021/ac034173t); [airPLS](https://doi.org/10.1039/b922045c)), and wavelet soft-thresholding ([Donoho 1995](https://doi.org/10.1109/18.382009)).

Before any transform or noisy-region filter affects calls, validation must use approved truth-labeled traces and synthetic major/secondary peaks, baseline drift, impulses, compressed peaks, homopolymers, and read ends. It must measure secondary-peak retention and both false-positive and false-negative variants.
