"""Bounded, explicitly clocked streaming primitives for research acquisition."""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class StreamInfo:
    sfreq: float
    channels: tuple[str, ...]
    units: tuple[str, ...]
    modality: str = "eeg"
    clock: str = "device"

    def __post_init__(self):
        if isinstance(self.sfreq, bool) or not np.isfinite(self.sfreq) or self.sfreq <= 0:
            raise ValueError("sfreq must be finite and positive")
        if not isinstance(self.channels, (tuple, list)) or not isinstance(self.units, (tuple, list)):
            raise ValueError("Channel names and units must be explicit sequences of strings")
        channels, units = tuple(self.channels), tuple(self.units)
        if not channels or len(channels) > 1024 or any(not isinstance(x, str) for x in channels) or len(set(channels)) != len(channels):
            raise ValueError("channels must be nonempty, unique strings (maximum 1024)")
        if len(units) != len(channels) or any(not isinstance(x, str) or not x for x in channels + units):
            raise ValueError("Each named channel requires an explicit unit")
        if not isinstance(self.modality, str) or not self.modality or not isinstance(self.clock, str) or not self.clock:
            raise ValueError("modality and clock must be explicit")
        object.__setattr__(self, "channels", channels)
        object.__setattr__(self, "units", units)


@dataclass(frozen=True)
class SampleBlock:
    data: np.ndarray
    timestamps: np.ndarray
    start_sample: int

    def __post_init__(self):
        if np.iscomplexobj(self.data) or np.iscomplexobj(self.timestamps):
            raise ValueError("Complex samples or timestamps require an explicit representation")
        data = np.array(self.data, dtype=np.float64, copy=True)
        timestamps = np.array(self.timestamps, dtype=np.float64, copy=True)
        if data.ndim != 2 or not data.shape[0] or not data.shape[1]:
            raise ValueError("data must be nonempty channels by samples")
        if timestamps.shape != (data.shape[1],) or not np.isfinite(timestamps).all():
            raise ValueError("One finite timestamp is required per sample")
        if not np.isfinite(data).all() or np.any(np.diff(timestamps) <= 0):
            raise ValueError("Values must be finite and timestamps strictly increasing")
        if isinstance(self.start_sample, bool) or not isinstance(self.start_sample, (int, np.integer)) or self.start_sample < 0:
            raise ValueError("start_sample must be a nonnegative integer")
        data.flags.writeable = False
        timestamps.flags.writeable = False
        object.__setattr__(self, "data", data)
        object.__setattr__(self, "timestamps", timestamps)

    @property
    def stop_sample(self):
        return self.start_sample + self.data.shape[1]


class Device(Protocol):
    info: StreamInfo

    def read(self, n_samples: int) -> SampleBlock: ...
    def close(self) -> None: ...


class RingBuffer:
    """Thread-safe latest-window buffer; never silently join discontinuous samples.

    A sequence gap or a timestamp gap clears the retained window. Overwritten
    samples and lost source samples have separate cumulative counters.
    """

    def __init__(self, capacity: int, n_channels: int, sfreq: float):
        if any(isinstance(x, bool) or not isinstance(x, int) or x < 1 for x in (capacity, n_channels)):
            raise ValueError("capacity and n_channels must be positive integers")
        if capacity * n_channels > 10_000_000:
            raise ValueError("Buffer exceeds 10000000-value resource limit")
        if not np.isfinite(sfreq) or sfreq <= 0:
            raise ValueError("sfreq must be finite and positive")
        self.capacity, self.n_channels, self.sfreq = capacity, n_channels, sfreq
        self._data = np.empty((n_channels, capacity))
        self._timestamps = np.empty(capacity)
        self._head = self._size = 0
        self._next = self._last_time = None
        self.dropped_samples = self.overwritten_samples = self.discontinuities = 0
        self._lock = RLock()

    def append(self, block: SampleBlock) -> bool:
        if block.data.shape[0] != self.n_channels:
            raise ValueError("Channel count mismatch")
        period = 1 / self.sfreq
        if block.timestamps.size > 1 and not np.allclose(np.diff(block.timestamps), period, rtol=.05, atol=1e-9):
            raise ValueError("Within-block timestamps do not match declared sampling frequency")
        with self._lock:
            if self._next is not None and block.start_sample < self._next:
                raise ValueError("Duplicate, overlapping, or out-of-order block")
            if self._last_time is not None and block.timestamps[0] <= self._last_time:
                raise ValueError("Timestamp clock moved backwards")
            gap = self._next is not None and block.start_sample != self._next
            time_gap = self._last_time is not None and not np.isclose(block.timestamps[0] - self._last_time, period, rtol=.05, atol=1e-9)
            discontinuous = gap or time_gap
            if discontinuous:
                self.dropped_samples += block.start_sample - self._next
                self.discontinuities += 1
                self._size = self._head = 0
            n = block.data.shape[1]
            self.overwritten_samples += max(0, self._size + n - self.capacity)
            # Work bounded by capacity even for unusually large source blocks.
            keep = min(n, self.capacity)
            indices = (self._head + np.arange(keep)) % self.capacity
            self._data[:, indices] = block.data[:, -keep:]
            self._timestamps[indices] = block.timestamps[-keep:]
            self._head = (self._head + keep) % self.capacity
            self._size = min(self.capacity, self._size + n)
            self._next, self._last_time = block.stop_sample, block.timestamps[-1]
            return discontinuous

    def snapshot(self) -> SampleBlock | None:
        with self._lock:
            if not self._size:
                return None
            indices = (self._head - self._size + np.arange(self._size)) % self.capacity
            return SampleBlock(self._data[:, indices], self._timestamps[indices], self._next - self._size)

    def diagnostics(self) -> dict:
        with self._lock:
            return {"retained_samples": self._size, "capacity": self.capacity,
                    "dropped_samples": self.dropped_samples,
                    "overwritten_samples": self.overwritten_samples,
                    "discontinuities": self.discontinuities}


class SimulatedDevice:
    """Deterministic analytical tones plus seeded noise, without real-time sleeping.

    read() advances a virtual device clock. Consumers may pace calls separately.
    This is a test source, not a model of a person's physiology.
    """

    def __init__(self, info: StreamInfo, seed: int = 42, frequency: float = 10., amplitude: float = 20.):
        if not np.isfinite(frequency) or not 0 < frequency < info.sfreq / 2:
            raise ValueError("frequency must be below Nyquist and positive")
        if not np.isfinite(amplitude) or amplitude <= 0:
            raise ValueError("amplitude must be finite and positive")
        self.info, self.frequency, self.amplitude = info, frequency, amplitude
        self._rng = np.random.default_rng(seed)
        self._next = 0
        self._closed = False

    def read(self, n_samples: int) -> SampleBlock:
        if self._closed:
            raise RuntimeError("Device is closed; create a new session to reconnect")
        if isinstance(n_samples, bool) or not isinstance(n_samples, int) or n_samples < 1 or n_samples > 1_000_000:
            raise ValueError("n_samples must be between 1 and 1000000")
        if n_samples * len(self.info.channels) > 10_000_000:
            raise ValueError("Read exceeds 10000000-value resource limit")
        timestamps = np.arange(self._next, self._next + n_samples) / self.info.sfreq
        phases = np.arange(len(self.info.channels))[:, None] / 7
        # Sample-major generation makes the stream independent of chunk sizes.
        noise = self._rng.normal(0, .02 * self.amplitude, (n_samples, len(self.info.channels))).T
        data = self.amplitude * np.sin(2 * np.pi * self.frequency * timestamps + phases) + noise
        block = SampleBlock(data, timestamps, self._next)
        self._next = block.stop_sample
        return block

    def close(self):
        self._closed = True
