"""Explicit offline affine clock calibration, never an automatic sync claim."""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ClockAlignment:
    scale: float
    offset: float
    residual_rms_s: float
    device_range: tuple[float, float]

    @classmethod
    def fit(cls, device_times, host_times):
        device = np.asarray(device_times, dtype=float)
        host = np.asarray(host_times, dtype=float)
        if device.ndim != 1 or device.size < 3 or host.shape != device.shape or not np.isfinite(device).all() or not np.isfinite(host).all() or np.any(np.diff(device) <= 0) or np.any(np.diff(host) <= 0):
            raise ValueError("At least three increasing finite paired calibration timestamps required")
        # Centering prevents unstable regression on large epoch timestamps.
        centered = device - device.mean()
        scale = float(np.dot(centered, host - host.mean()) / np.dot(centered, centered))
        offset = float(host.mean() - scale * device.mean())
        residual = float(np.sqrt(np.mean((host - (device * scale + offset))**2)))
        if not np.isfinite([scale, offset, residual]).all() or scale <= 0:
            raise ValueError("Clock fit is numerically unstable")
        return cls(scale, offset, residual, (float(device[0]), float(device[-1])))

    def transform(self, timestamps, allow_extrapolation=False):
        values = np.asarray(timestamps, dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("Timestamps must be finite")
        if not allow_extrapolation and np.any((values < self.device_range[0]) | (values > self.device_range[1])):
            raise ValueError("Timestamp outside calibration interval; explicit extrapolation required")
        return values * self.scale + self.offset
