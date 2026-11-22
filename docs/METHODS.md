# Scientific methods and limitations (v0.2)

**Status:** algorithm-level numerical verification on known synthetic signals plus independent Welch PSD agreement with MNE-Python. **Not clinical validation.** No sensitivity, specificity, diagnostic thresholds or therapeutic claims have been established.

## Signal conventions

- Input matrix: `(channels, samples)` with amplitudes in **microvolts (µV)** and uniform sampling frequency in **Hz**.
- CSV time values are in seconds. If a time column is supplied, its sample interval is checked against the declared `sfreq` (2% median tolerance, 5% individual-step deviation); irregular recordings must be explicitly resampled before analysis.
- CSV user-specified amplitude units are converted to µV; EDF-import EEG and EMG samples are selected **separately** and converted from MNE internal volts to µV.
- EDF channel typing depends on labels. Verify recording metadata and channel units manually. Unrecognized or mislabeled EMG may be misclassified upstream; this tool refuses a modality when no channel of that type is found.

## Preprocessing (offline only)

1. Missing data: interpolate interior gaps only when both the total missing fraction is ≤5% and each contiguous gap is ≤0.1 s (configurable). **Never interpolate across missing start/end samples**, or fabricate longer gaps.
2. Remove each channel mean; this is not a substitute for proper reference selection or drift correction.
3. Optional 50/60 Hz notch via a second-order IIR (`iirnotch`, Q=30) applied forward and backward. Notch removes energy near mains frequency, and can alter the spectral distribution.
4. Optional Butterworth IIR highpass, lowpass or bandpass (order four), represented as second-order sections, applied with `sosfiltfilt`. Forward/backward filtering is acausal and changes the magnitude response (effectively squaring it). It **cannot** be used unchanged for real-time BCI control.
5. **EEG defaults:** 0.1 Hz high-pass, no software low-pass, optional 50 Hz notch when Nyquist permits. A 4 s Welch window is chosen when the recording is long enough. No low-pass avoids silently discarding 30–45 Hz gamma. However, this does *not* ensure adequate anti-aliasing; hardware acquisition and other high-frequency artifacts need independent review.
6. **EMG defaults:** high-pass `min(20 Hz, 0.1 × sampling rate)` and 450 Hz low-pass only when Nyquist exceeds 450 Hz (sampling rate >900 Hz). At ≤900 Hz the low-pass is omitted; at <1000 Hz an explicit bandwidth warning is emitted regardless. This does **not** recover frequencies lost or aliased before sampling. Acquisition bandwidth and anti-aliasing still need review; do not interpret low-rate recordings as full-band sEMG.

## Spectral density and EEG bands

- Welch PSD with Hann window, 50% overlap and density scaling; units µV²/Hz. Numerical integration over frequency gives variance (µV²), subject to estimator and filter limitations.
- Bands: delta 0.5–4, theta 4–8, alpha 8–13, beta 13–30 and gamma 30–45 Hz. These are pragmatic descriptive conventions; literature definitions vary.
- Absolute band power is computed by trapezoidal integration with PSD interpolation at boundaries. Bands that extend beyond Nyquist are **null/unavailable** (never zero). A `*_coverage` field indicates fractional observed bandwidth.
- Relative powers use the denominator 0.5–min(45 Hz, Nyquist) and are comparable across recordings **only** when their frequency support and preprocessing are equivalent.
- **Important limitation at band edges:** A 0.5 Hz sine has part of its tapered spectral energy below 0.5 Hz, and truncating the integral at 0.5 Hz gives ~50% of its nominal power. A 0.75 Hz sine with a 2-second window can be underestimated. Such numerical effects are not a loss of neural amplitude or an indication of pathology. Use longer segments, explicit spectral resolution and a scientifically justified integration convention.
- Avoid scientific interpretation of delta when highpass ≥0.5 Hz or gamma when lowpass ≤45 Hz. The tool warns on these settings.

## Descriptive signal features

- Hjorth activity = variance of signal in µV²; mobility = sqrt(variance(first numerical derivative)/activity) in 1/s; complexity = mobility(derivative)/mobility(signal), dimensionless. Finite differences are multiplied by the sampling frequency.
- Spectrogram via SciPy Welch-compatible short-time PSD. Time axis refers to segment centers, not event onsets.
- Magnitude-squared coherence (0–1) requires at least two overlapping Welch segments and nonconstant channels. A single-segment estimate is rejected because it can be trivially unity for unrelated signals. The minimum is not a statistical reliability criterion. Shared reference, volume conduction, sample size and common noise can inflate coherence; it is *not* proof of neural connectivity.
- EMG RMS, mean absolute value, total waveform length and PSD median frequency are descriptive and depend strongly on bandwidth, electrode geometry and acquisition conditions. **Median frequency alone does not diagnose fatigue.**

## Signal quality and review flags

- Channel QC includes RMS, p2p, median, standard deviation, percent of small step changes and residual 50/60 Hz power fraction.
- Mains fractions reflect the **post-filter** signal; these cannot quantify the raw interference after a notch. Fractions are null when the frequency band is unavailable under Nyquist, rather than falsely zero.
- Heuristic event candidates use raw (short-gap-interpolated, unfiltered) signal median/MAD: `median absolute deviation = 1.4826 × median(|x − median(x)|)`. Mark windows if any sample exceeds `max(20 µV, threshold × MAD)` relative to the recording median or p2p ≤ default 0.15 µV. These are **review candidates**, not clinically validated artifact classifiers.

## Independent verification included

- The 10, 20, 35 and 42 Hz 10 µV peak synthetic sinusoidal tones recover power close to the theoretical 50 µV² under the corrected default analysis.
- The 200 Hz 100 µV peak sEMG tone at 500 Hz sample rate now recovers ~70.71 µV RMS rather than ~1.30 µV before the corrected default filtering. It still triggers a warning about the 500 Hz sampling limit.
- `scipy.signal.welch` PSD is cross-checked against `mne.time_frequency.psd_array_welch` after converting V²/Hz ↔ µV²/Hz. These library interfaces may share numerical dependencies; this is a cross-library consistency check, not independent scientific peer review.
- End-to-end CSV timestamp checks, mixed-label synthetic EDF file round-trip, channel separation, interpolation limits, coherence sanity checks and frequency-domain transient localization are covered by automated tests.

## Unvalidated domains

- The proposed v0.3 development pilot evaluates a small public PhysioNet EEG subset for technical interoperability only; no real EMG or independent physiological/clinical validation is established.
- No device hardware calibration, analog antialias verification, electrode impedance evaluation, reference montage verification, or inter-device synchronization verification.
- No clinically annotated artifact labels, blinded expert assessment, statistical performance confidence intervals, classification accuracy, real-time safety evaluation or medical device regulatory review.
- Do not use it to assess seizures, abnormal EEG, neurological diagnoses, muscle disease, patient treatment or BCI safety-critical control.

## External references

1. SciPy Welch estimator: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html
2. SciPy `filtfilt` and zero-phase filtering: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.filtfilt.html
3. MNE EDF import and channel types: https://mne.tools/stable/generated/mne.io.read_raw_edf.html
4. MNE filtering background and tradeoffs: https://mne.tools/stable/auto_tutorials/preprocessing/25_background_filtering.html
5. Merletti & Cerone (2020), Surface EMG best practices: https://www.robertomerletti.it/assets/pdfs/publications/2020_Tutorial_Merletti_Cerone.pdf
6. Surface EMG acquisition and filtering review: https://pmc.ncbi.nlm.nih.gov/articles/PMC7594523/
7. Reference effects on EEG coherence: https://pmc.ncbi.nlm.nih.gov/articles/PMC2891575/
8. PhysioNet EEG Motor Movement/Imagery database (future independent validation): https://physionet.org/content/eegmmidb/1.0.0/
9. PhysioNet Sleep-EDF Expanded (future independent validation): https://physionet.org/content/sleep-edfx/1.0.0/
10. Welch, P. D. (1967), IEEE Transactions on Audio and Electroacoustics, 15(2), 70–73.

## Explicit development-policy metadata

The proposed v0.3 exports software versions, mean-removal status and odd-reflection padding: 9 samples for the notch, 15 for a single fourth-order high/low-pass, and 27 for the combined band-pass. These match the prior SciPy defaults; processing defaults are not silently changed. The [real-data report](real_world/REPORT.md) documents the comparison with independently configured MNE and the material effect of changing padding policy. Raw channel metrics and raw PSD are available separately from processed results.
