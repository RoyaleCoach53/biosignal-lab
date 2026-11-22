"""Typed, immutable configuration and validated recording containers."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
import numpy as np
from ._version import __version__
from importlib.metadata import version

Modality = Literal["eeg", "emg"]
EEG_BANDS: dict[str, tuple[float, float]] = {
    "delta": (0.5, 4.0), "theta": (4.0, 8.0), "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0), "gamma": (30.0, 45.0),
}

@dataclass(frozen=True)
class Recording:
    data_uv: np.ndarray     # shape: channels x samples; unit always microvolts
    sfreq: float
    channels: tuple[str, ...]
    modality: Modality = "eeg"
    source: str = "unknown"

    def __post_init__(self) -> None:
        data = np.asarray(self.data_uv, dtype=np.float64)
        if data.ndim != 2 or data.shape[0] < 1 or data.shape[1] < 16:
            raise ValueError("Expected channels x samples, at least one channel and 16 samples")
        if not np.isfinite(self.sfreq) or self.sfreq <= 0:
            raise ValueError("Sampling frequency must be finite and positive")
        if len(self.channels) != data.shape[0] or len(set(self.channels)) != len(self.channels):
            raise ValueError("Channel names must be unique and match data shape")
        if self.modality not in ("eeg", "emg"):
            raise ValueError("Modality must be eeg or emg")
        if np.any(np.isinf(data)):
            raise ValueError("Infinite signal values are not supported")
        if np.all(~np.isfinite(data)):
            raise ValueError("At least one signal value must be finite")
        object.__setattr__(self, "data_uv", data)

    @property
    def duration_s(self) -> float:
        return self.data_uv.shape[1] / self.sfreq

@dataclass(frozen=True)
class AnalysisConfig:
    modality: Modality = "eeg"
    highpass_hz: float | None = 0.1
    lowpass_hz: float | None = None
    notch_hz: float | None = 50.0
    notch_quality: float = 30.0
    window_s: float = 4.0
    artifact_window_s: float = 1.0
    artifact_threshold_mad: float = 8.0
    flatline_tolerance_uv: float = 0.15
    max_missing_fraction: float = 0.05
    max_gap_s: float = 0.1

    def validate(self, sfreq: float, n_samples: int) -> None:
        nyquist = sfreq / 2
        if self.modality not in ("eeg", "emg"):
            raise ValueError("Unsupported signal modality")
        if self.highpass_hz is not None and not (np.isfinite(self.highpass_hz) and 0 < self.highpass_hz < nyquist):
            raise ValueError("High-pass must be between 0 and Nyquist")
        if self.lowpass_hz is not None and not (np.isfinite(self.lowpass_hz) and 0 < self.lowpass_hz < nyquist):
            raise ValueError("Low-pass must be between 0 and Nyquist")
        if self.highpass_hz is not None and self.lowpass_hz is not None:
            if self.highpass_hz >= self.lowpass_hz:
                raise ValueError("High-pass must be less than low-pass")
        if self.notch_hz is not None and not (np.isfinite(self.notch_hz) and 0 < self.notch_hz < nyquist):
            raise ValueError("Notch must be between 0 and Nyquist")
        if self.notch_quality <= 0 or not np.isfinite(self.notch_quality):
            raise ValueError("Notch quality must be finite and positive")
        if not (np.isfinite(self.window_s) and 0 < self.window_s <= n_samples / sfreq):
            raise ValueError("Window must fit within recording")
        if not (np.isfinite(self.artifact_window_s) and self.artifact_window_s > 0):
            raise ValueError("Artifact review window must be finite and positive")
        if not (np.isfinite(self.artifact_threshold_mad) and 0 < self.artifact_threshold_mad < 100):
            raise ValueError("Artifact threshold must be between 0 and 100")
        if self.flatline_tolerance_uv < 0 or not np.isfinite(self.flatline_tolerance_uv):
            raise ValueError("Flatline tolerance must be nonnegative")
        if not (np.isfinite(self.max_missing_fraction) and 0 <= self.max_missing_fraction < 1):
            raise ValueError("Max missing fraction must be between 0 and 1")
        if not (np.isfinite(self.max_gap_s) and self.max_gap_s > 0):
            raise ValueError("Max gap duration must be finite and positive")

@dataclass
class AnalysisResults:
    recording: Recording
    processed_uv: np.ndarray
    frequencies_hz: np.ndarray
    psd_uv2_per_hz: np.ndarray
    channel_metrics: list[dict[str, float | str | bool]]
    band_powers: list[dict[str, float | str | None]]
    artifact_intervals: list[dict[str, float | str]]
    warnings: list[str] = field(default_factory=list)
    config: AnalysisConfig = field(default_factory=AnalysisConfig)
    raw_frequencies_hz: np.ndarray | None = None
    raw_psd_uv2_per_hz: np.ndarray | None = None
    raw_channel_metrics: list[dict] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "tool": "BioSignal Lab", "version": __version__, "modality": self.recording.modality,
            "source": self.recording.source, "sfreq_hz": self.recording.sfreq,
            "duration_s": round(self.recording.duration_s, 4),
            "n_channels": len(self.recording.channels), "n_samples": self.recording.data_uv.shape[1],
            "config": self.config.__dict__, "channels": self.channel_metrics,
            "raw_channels": self.raw_channel_metrics,
            "raw_metrics_note": "Permitted short interior gaps are interpolated; raw metrics precede mean removal/filters, while raw PSD removes each Welch segment mean.",
            "software": {name: version(name) for name in ("numpy", "scipy", "pandas")},
            "processing": {"mean_removed": True, "filter_order": 4,
                           "direction": "forward_backward", "padding": "odd",
                           "notch_pad_samples": 9 if self.config.notch_hz else None,
                           "butterworth_pad_samples": (27 if self.config.highpass_hz and self.config.lowpass_hz else 15)
                           if self.config.highpass_hz or self.config.lowpass_hz else None},
            "bands": self.band_powers, "artifact_candidates": self.artifact_intervals,
            "warnings": self.warnings, "disclaimer": "Research/education only. No medical diagnosis.",
        }
