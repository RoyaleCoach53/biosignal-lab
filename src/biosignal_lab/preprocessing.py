"""Zero-phase digital filtering with explicit validation and NaN interpolation."""
from __future__ import annotations
import numpy as np
from scipy.signal import butter, sosfiltfilt, iirnotch, filtfilt, detrend
from .models import AnalysisConfig


def fill_short_gaps(data: np.ndarray, max_missing_fraction: float,
                    max_gap_samples: int | None = None) -> tuple[np.ndarray, list[str]]:
    """Interpolate only *interior* missing intervals within documented limits.

    Never extrapolate missing samples at recording edges. Enforcing a maximum
    contiguous gap avoids silently fabricating long sections of physiology.
    """
    out = np.asarray(data, dtype=float).copy()
    warnings = []
    for i, row in enumerate(out):
        valid = np.isfinite(row)
        missing_fraction = 1 - float(np.mean(valid))
        if missing_fraction == 0:
            continue
        if missing_fraction > max_missing_fraction or np.sum(valid) < 2:
            raise ValueError(f"Channel {i}: {missing_fraction:.1%} missing exceeds limit")
        if not valid[0] or not valid[-1]:
            raise ValueError(f"Channel {i}: missing boundary samples cannot be interpolated safely")
        missing = ~valid
        starts = np.flatnonzero(missing & np.r_[True, valid[:-1]])
        ends = np.flatnonzero(missing & np.r_[valid[1:], True])
        gap_lengths = ends - starts + 1
        if max_gap_samples is not None and np.any(gap_lengths > max_gap_samples):
            raise ValueError(f"Channel {i}: missing gap exceeds maximum interpolation duration")
        x = np.arange(row.size)
        row[missing] = np.interp(x[missing], x[valid], row[valid])
        warnings.append(f"Channel {i}: {missing_fraction:.2%} missing samples interpolated")
    return out, warnings


def preprocess(data_uv: np.ndarray, sfreq: float, config: AnalysisConfig) -> tuple[np.ndarray, list[str]]:
    config.validate(sfreq, data_uv.shape[1])
    out, warnings = fill_short_gaps(data_uv, config.max_missing_fraction,
                                    max_gap_samples=int(sfreq * config.max_gap_s))
    if out.shape[1] < max(16, int(0.5 * sfreq)):
        warnings.append("Short recording: filter edge effects may dominate")
    # Detrend first, before zero-phase filtering, to avoid fitting artifacts to baseline.
    out = detrend(out, axis=1, type="constant")
    if config.notch_hz is not None:
        b, a = iirnotch(config.notch_hz, config.notch_quality, fs=sfreq)
        try:
            out = filtfilt(b, a, out, axis=1)
        except ValueError as exc:
            raise ValueError("Not enough samples for notch filtering") from exc
    hp, lp = config.highpass_hz, config.lowpass_hz
    if hp is not None and lp is not None:
        sos = butter(4, [hp, lp], btype="bandpass", fs=sfreq, output="sos")
    elif hp is not None:
        sos = butter(4, hp, btype="highpass", fs=sfreq, output="sos")
    elif lp is not None:
        sos = butter(4, lp, btype="lowpass", fs=sfreq, output="sos")
    else:
        sos = None
    if sos is not None:
        try:
            out = sosfiltfilt(sos, out, axis=1)
        except ValueError as exc:
            raise ValueError("Not enough samples for band filter") from exc
    return out, warnings
