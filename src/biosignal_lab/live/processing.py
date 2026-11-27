"""Stateful causal filtering and bounded sliding-window spectral monitoring."""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import numpy as np
from scipy.signal import sosfilt, welch

from .core import RingBuffer, SampleBlock, StreamInfo


@dataclass(frozen=True)
class LiveResult:
    block: SampleBlock
    frequencies: np.ndarray | None
    psd: np.ndarray | None
    diagnostics: dict


class LiveProcessor:
    """Zero-state SOS filtering, reset on discontinuity; no acausal padding.

    warmup_s is an explicit reporting exclusion, not a guarantee of settling.
    Different filters have different transients. PSD is absent until a complete
    contiguous window after the exclusion exists. PSD units are input-unit²/Hz.
    """

    def __init__(self, info: StreamInfo, sos=None, window_s: float = 2., warmup_s: float = 1.):
        if not np.isfinite(window_s) or window_s <= 0 or not np.isfinite(warmup_s) or warmup_s < 0:
            raise ValueError("Window must be positive and warmup nonnegative")
        window = round(window_s * info.sfreq)
        if window < 4 or window * len(info.channels) > 10_000_000:
            raise ValueError("Spectral window must have >=4 samples and <=10000000 values")
        self.info, self.window = info, window
        self.warmup = round(warmup_s * info.sfreq) if sos is not None else 0
        self._remaining = self.warmup
        self._source = RingBuffer(1, len(info.channels), info.sfreq)
        self._filtered = RingBuffer(window, len(info.channels), info.sfreq)
        self.sos = None if sos is None else np.array(sos, dtype=float, copy=True)
        if self.sos is not None and (self.sos.ndim != 2 or self.sos.shape[1] != 6 or not np.isfinite(self.sos).all()):
            raise ValueError("SOS must have shape sections by 6 and finite coefficients")
        self._state = None if self.sos is None else np.zeros((len(self.sos), len(info.channels), 2))
        # Validate denominator normalization and filter validity before accepting data.
        if self.sos is not None:
            if np.any(self.sos[:, 3] != 1) or any(np.any(np.abs(np.roots(row[3:])) >= 1) for row in self.sos):
                raise ValueError("SOS must be normalized and strictly stable")

    def process(self, block: SampleBlock) -> LiveResult:
        start = perf_counter()
        if np.max(np.abs(block.data)) > 1e150:
            raise ValueError("Signal magnitude exceeds stable squared-power calculation range")
        gap = self._source.append(block)
        if gap:
            self._remaining = self.warmup
            self._filtered = RingBuffer(self.window, len(self.info.channels), self.info.sfreq)
            if self._state is not None:
                self._state.fill(0)
        if self.sos is None:
            data = block.data
        else:
            data, self._state = sosfilt(self.sos, block.data, axis=1, zi=self._state)
        output = SampleBlock(data, block.timestamps, block.start_sample)
        excluded = min(self._remaining, data.shape[1])
        self._remaining -= excluded
        if excluded < data.shape[1]:
            self._filtered.append(SampleBlock(data[:, excluded:], block.timestamps[excluded:], block.start_sample + excluded))
        retained = self._filtered.snapshot()
        frequencies = psd = None
        if retained is not None and retained.data.shape[1] == self.window:
            frequencies, psd = welch(retained.data, fs=self.info.sfreq, nperseg=self.window,
                                     noverlap=0, detrend="constant", axis=1)
        diagnostics = self._source.diagnostics()
        diagnostics.update({"discontinuity": gap, "filter_reset": gap and self.sos is not None,
                            "warmup_samples_remaining": self._remaining,
                            "psd_ready": psd is not None,
                            "processing_seconds": perf_counter() - start,
                            "input_rms": np.sqrt(np.mean(block.data**2, axis=1)).tolist(),
                            "flat_channels": (np.ptp(block.data, axis=1) == 0).tolist(),
                            "clock": self.info.clock,
                            "latency_scope": "CPU processing duration only; excludes device/network/display latency"})
        return LiveResult(output, frequencies, psd, diagnostics)
