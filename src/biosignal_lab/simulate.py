"""Deterministic synthetic educational signals with known components and artifacts."""
from __future__ import annotations
import numpy as np
from .models import Recording


def synthetic_recording(*, duration_s: float = 30, sfreq: float = 250,
                        n_channels: int = 8, modality: str = "eeg", seed: int = 42,
                        with_artifacts: bool = True) -> Recording:
    if not 1 <= n_channels <= 128 or not 1 <= duration_s <= 3600:
        raise ValueError("Channels must be 1..128; duration 1..3600 seconds")
    if not 40 <= sfreq <= 4000:
        raise ValueError("Sampling frequency must be 40..4000 Hz")
    count = int(round(duration_s * sfreq))
    t = np.arange(count) / sfreq
    rng = np.random.default_rng(seed)
    x = np.zeros((n_channels, count), dtype=float)
    for ch in range(n_channels):
        if modality == "eeg":
            # Do not alias an unrepresentable demo component into a lower band.
            tones = [(22, 10, ch * .24), (10, 6, ch * .6), (4, 20, 0), (3, 50, 0)]
            for amplitude, frequency, phase in tones:
                if frequency < sfreq / 2:
                    x[ch] += amplitude * np.sin(2 * np.pi * frequency * t + phase)
            x[ch] += rng.normal(0, 5, count)
            if with_artifacts and duration_s >= 8:
                center = int(5 * sfreq)
                width = max(5, int(.12 * sfreq))
                xx = np.arange(count)
                x[ch] += 180 * np.exp(-0.5 * ((xx - center) / width) ** 2)
        else:
            # Envelope-modulated, band-limited noise approximates educational EMG texture.
            high = rng.normal(size=count)
            kernel = np.ones(max(2, int(sfreq // 80)))
            smoothed = np.convolve(high, kernel / kernel.size, mode="same")
            envelope = .2 + .8 * ((np.sin(2 * np.pi * .3 * t) + 1) / 2)
            x[ch] = 55 * envelope * (high - smoothed) + rng.normal(0, 2, count)
    if modality not in ("eeg", "emg"):
        raise ValueError("Unsupported modality")
    return Recording(x, float(sfreq), tuple(f"Ch{i+1}" for i in range(n_channels)),
                     modality=modality, source=f"synthetic_{modality}_seed_{seed}")
