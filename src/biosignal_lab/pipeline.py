"""Reproducible educational analysis, with explicit methodological warnings."""
from __future__ import annotations
from .models import Recording, AnalysisConfig, AnalysisResults
from .preprocessing import preprocess, fill_short_gaps
from .analysis import (compute_psd, band_powers, detect_artifacts, quality_metrics,
                       hjorth_parameters, emg_descriptors)


def default_config(modality: str, sfreq: float, window_s: float | None = None) -> AnalysisConfig:
    """Analysis defaults preserving the EEG bands and not destroying typical sEMG.

    Defaults are not acquisition recommendations. The user must document analog
    anti-aliasing, reference and hardware bandwidth for scientific interpretation.
    """
    nyquist = sfreq / 2
    if window_s is None:
        window_s = 4.0 if modality == "eeg" else 2.0
    notch = 50.0 if nyquist > 50.0 else None
    if modality == "emg":
        # Avoid artificially deleting 200–450 Hz EMG in recordings with
        # inadequate sample rates: flag those recordings instead.
        return AnalysisConfig(modality="emg", highpass_hz=min(20., nyquist * 0.2),
                              lowpass_hz=450.0 if nyquist > 450.0 else None,
                              notch_hz=notch, window_s=window_s)
    if modality != "eeg":
        raise ValueError("Unsupported modality")
    # 0.1 Hz HP preserves 0.5 Hz delta more faithfully than 1 Hz. No digital
    # LP prevents cutting off 30–45 Hz gamma. This is NOT an antialias filter.
    return AnalysisConfig(modality="eeg", highpass_hz=0.1 if nyquist > .1 else None,
                          lowpass_hz=None, notch_hz=notch, window_s=window_s)


def analyze(recording: Recording, config: AnalysisConfig | None = None) -> AnalysisResults:
    if config is None:
        config = default_config(recording.modality, recording.sfreq,
                                window_s=min(4. if recording.modality == "eeg" else 2.,
                                             recording.duration_s))
    if recording.modality != config.modality:
        raise ValueError("Recording modality and configuration modality must match")
    clean, warnings = preprocess(recording.data_uv, recording.sfreq, config)
    freqs, psd = compute_psd(clean, recording.sfreq, config.window_s)
    qc = quality_metrics(clean, recording.sfreq, recording.channels,
                         freqs, psd, config.flatline_tolerance_uv)
    for i, row in enumerate(qc):
        row.update({key: round(val, 5) for key, val in
                    hjorth_parameters(clean[i], recording.sfreq).items()})
        if recording.modality == "emg":
            row.update({key: round(val, 5) for key, val in
                        emg_descriptors(clean[i], recording.sfreq).items()})
    # Raw data are used to flag candidates. Gap filling is replicated solely for
    # detection; we never silently interpret missing samples as 'clean'.
    raw_filled, _ = fill_short_gaps(recording.data_uv, config.max_missing_fraction,
                                    max_gap_samples=int(recording.sfreq * config.max_gap_s))
    artifacts = detect_artifacts(raw_filled, recording.sfreq, recording.channels,
                                 window_s=min(config.artifact_window_s, recording.duration_s),
                                 threshold_mad=config.artifact_threshold_mad,
                                 flatline_tolerance_uv=config.flatline_tolerance_uv)
    if recording.modality == "emg":
        bands = []
        warnings.append("EEG frequency-band powers are not appropriate for EMG and are omitted")
        if recording.sfreq < 1000:
            warnings.append("EMG sampling rate <1000 Hz: broadband surface EMG (to ~450 Hz) cannot be characterized; confirm analog anti-aliasing. Spectral summaries are bandwidth-limited")
        if config.lowpass_hz is not None and config.lowpass_hz < 450:
            warnings.append("EMG low-pass cutoff <450 Hz attenuates upper-band energy and can change RMS and median frequency; compare only matched acquisition/filter settings")
    else:
        bands = band_powers(freqs, psd, recording.channels)
        if recording.sfreq < 90:
            warnings.append("EEG sample rate below 90 Hz: 30–45 Hz gamma band is incompletely observable; unavailable bands are null, not zero")
        if config.lowpass_hz is not None and config.lowpass_hz <= 45:
            warnings.append("EEG low-pass cutoff <=45 Hz attenuates gamma-band measurements; avoid interpreting band power as raw physiological power")
        if config.highpass_hz is not None and config.highpass_hz >= .5:
            warnings.append("EEG high-pass cutoff >=0.5 Hz can attenuate the delta band (0.5–4 Hz)")
        if config.window_s < 4:
            warnings.append("EEG Welch window <4 s: low-delta (<1 Hz) estimates are particularly sensitive to spectral resolution and band-edge leakage")
        if recording.duration_s < 10:
            warnings.append("Short EEG recording <10 s: low-frequency filter transients and PSD estimates require caution")
    if config.notch_hz is not None:
        warnings.append("Line-noise ratios refer to the AFTER-NOTCH signal; low residual values do not measure the original interference")
    if any("flatline" in b["reason"] for b in artifacts):
        warnings.append("Possible flatline segments detected: review electrodes, acquisition and recordings")
    return AnalysisResults(recording, clean, freqs, psd, qc, bands, artifacts, warnings, config)
