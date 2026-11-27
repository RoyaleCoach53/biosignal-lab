"""Deterministic epoch features; no labels, fitting, or hidden normalisation."""
from __future__ import annotations

import numpy as np
from scipy.signal import welch


def extract_epoch_features(epochs, sfreq: float, modality: str = "eeg"):
    """Return ``(features, names)`` for epochs x channels x samples.

    Amplitudes retain the caller's units. Power uses those units squared. This
    function does not infer a diagnosis, reference, montage or amplitude units.
    EEG bands require complete Nyquist coverage and a minimum two-second epoch;
    EMG frequencies describe the measured bandwidth rather than full muscle EMG.
    """
    data = np.asarray(epochs, dtype=float)
    if data.ndim != 3 or min(data.shape) < 1 or data.shape[2] < 16:
        raise ValueError("Expected nonempty epochs x channels x samples, at least 16 samples")
    if not np.isfinite(data).all() or not np.isfinite(sfreq) or sfreq <= 0:
        raise ValueError("Features require finite data and a positive sampling frequency")
    if modality not in {"eeg", "emg"}:
        raise ValueError("Feature modality must be eeg or emg")
    centered = data - data.mean(axis=-1, keepdims=True)
    values = [("rms", np.sqrt(np.mean(centered ** 2, axis=-1))),
              ("mav", np.mean(np.abs(centered), axis=-1)),
              ("peak_to_peak", np.ptp(centered, axis=-1))]
    frequencies, psd = welch(centered, fs=sfreq, axis=-1,
                             nperseg=min(data.shape[-1], max(16, int(2 * sfreq))))
    df = frequencies[1] - frequencies[0]
    # Rectangular bin integration has explicit grid boundaries and avoids silently
    # interpolating a boundary beyond the representable bandwidth.
    if modality == "eeg":
        if sfreq / 2 < 45 or data.shape[-1] / sfreq < 2:
            raise ValueError("EEG band features require Nyquist >=45 Hz and >=2-second epochs")
        for name, low, high in [("delta", .5, 4), ("theta", 4, 8), ("alpha", 8, 13),
                                ("beta", 13, 30), ("gamma", 30, 45)]:
            mask = (frequencies >= low) & (frequencies < high)
            if not mask.any():
                raise ValueError(f"No spectral bins represent the {name} band")
            values.append((name + "_power", psd[..., mask].sum(axis=-1) * df))
    else:
        delta = np.diff(centered, axis=-1)
        values.extend([("waveform_length", np.abs(delta).sum(axis=-1)),
                       ("integrated_emg", np.abs(centered).sum(axis=-1) / sfreq)])
        total = psd.sum(axis=-1)
        if np.any(total <= np.finfo(float).tiny):
            raise ValueError("EMG frequency features are undefined for a constant channel")
        values.append(("mean_frequency_hz", (psd * frequencies).sum(axis=-1) / total))
        median_indices = (psd.cumsum(axis=-1) < total[..., None] / 2).sum(axis=-1)
        values.append(("median_frequency_hz", frequencies[median_indices]))
    columns, names = [], []
    for channel in range(data.shape[1]):
        for name, feature in values:
            columns.append(feature[:, channel])
            names.append(f"ch{channel + 1}:{name}")
    features = np.column_stack(columns)
    if not np.isfinite(features).all():
        raise ValueError("Feature arithmetic overflow; rescale the input explicitly")
    return features, tuple(names)
