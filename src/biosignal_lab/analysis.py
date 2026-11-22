"""Research-only descriptive EEG/EMG spectral and quality metrics."""
from __future__ import annotations
import numpy as np
from scipy.signal import welch
from scipy.integrate import trapezoid
from .models import EEG_BANDS


def compute_psd(data_uv: np.ndarray, sfreq: float, window_s: float = 2.0):
    """Welch PSD in µV²/Hz for input amplitudes in µV."""
    values = np.asarray(data_uv, dtype=float)
    if values.ndim != 2 or values.shape[1] < 16 or not np.all(np.isfinite(values)):
        raise ValueError("PSD requires a finite channel-by-sample array (>=16 samples)")
    if not np.isfinite(sfreq) or not np.isfinite(window_s) or sfreq <= 0 or window_s <= 0:
        raise ValueError("PSD requires finite positive sampling frequency and window")
    nperseg = min(values.shape[1], max(16, int(round(sfreq * window_s))))
    freqs, power = welch(values, fs=sfreq, axis=1, window="hann", nperseg=nperseg,
                         noverlap=nperseg // 2, detrend="constant", scaling="density")
    return freqs, power


def _integrate(freqs: np.ndarray, power: np.ndarray, low: float, high: float) -> float:
    """Trapezoid PSD integration with interpolated edges, restricted to recorded support."""
    if high <= low or low >= freqs[-1]:
        return 0.0
    low = max(low, float(freqs[0]))
    high = min(high, float(freqs[-1]))
    if high <= low:
        return 0.0
    f = np.r_[low, freqs[(freqs > low) & (freqs < high)], high]
    p = np.interp(f, freqs, power)
    return float(trapezoid(p, f))


def band_powers(freqs: np.ndarray, power: np.ndarray, channels: tuple[str, ...]):
    """EEG bands in µV². Mark bands beyond Nyquist *unavailable*, not zero.

    Relative power is fraction of observed 0.5–min(45, Nyquist) Hz power;
    coverage notes qualify comparison across sampling rates.
    """
    results = []
    max_hz = float(freqs[-1]); upper = min(45.0, max_hz)
    for i, name in enumerate(channels):
        row: dict[str, float | str | None] = {"channel": name}
        denom = _integrate(freqs, power[i], 0.5, upper)
        for band, (lo, hi) in EEG_BANDS.items():
            coverage = max(0., min(hi, max_hz) - lo) / (hi - lo)
            row[f"{band}_coverage"] = float(coverage)
            # An unavailable gamma band must not be reported as zero power.
            val = _integrate(freqs, power[i], lo, hi) if coverage >= (1. - 1e-10) else None
            row[f"{band}_uv2"] = val
            row[f"{band}_relative"] = float(val / denom) if val is not None and denom > 0 else None
        row["total_0p5_to_upper_uv2"] = float(denom)
        row["total_upper_hz"] = float(upper)
        results.append(row)
    return results


def detect_artifacts(data_uv: np.ndarray, sfreq: float, channels: tuple[str, ...],
                     *, window_s: float, threshold_mad: float, flatline_tolerance_uv: float):
    """Flag heuristic amplitude outliers / flatline windows; *never* diagnose artifacts."""
    length = max(8, int(round(window_s * sfreq)))
    result = []
    for idx, name in enumerate(channels):
        x = data_uv[idx]
        # NaNs from the raw recording are tolerated elsewhere, but do not infer
        # artifact absence if missing values invalidate this window.
        if not np.all(np.isfinite(x)):
            raise ValueError("Artifact review requires gap-filled finite samples")
        med = float(np.median(x))
        mad = float(1.4826 * np.median(np.abs(x - med)))
        threshold = max(20.0, threshold_mad * mad)
        for start in range(0, x.size, length):
            end = min(start + length, x.size)
            segment = x[start:end]
            if segment.size < max(8, length // 4):
                continue
            p2p = float(np.ptp(segment))
            reasons = []
            if p2p <= flatline_tolerance_uv:
                reasons.append("flatline_candidate")
            if float(np.max(np.abs(segment - med))) > threshold:
                reasons.append("amplitude_outlier_candidate")
            if reasons:
                result.append({"channel": name, "start_s": round(start / sfreq, 3),
                               "end_s": round(end / sfreq, 3), "reason": ",".join(reasons),
                               "peak_to_peak_uv": round(p2p, 4)})
    return result


def quality_metrics(data_uv: np.ndarray, sfreq: float, channels: tuple[str, ...],
                    freqs: np.ndarray, psd: np.ndarray, tolerance_uv: float):
    results = []
    for i, name in enumerate(channels):
        row = data_uv[i]
        rms = float(np.sqrt(np.mean(row ** 2)))
        noise50 = _integrate(freqs, psd[i], 49, 51) if freqs[-1] >= 51 else None
        noise60 = _integrate(freqs, psd[i], 59, 61) if freqs[-1] >= 61 else None
        broad = _integrate(freqs, psd[i], 1, 90)
        delta = np.abs(np.diff(row))
        results.append({
            "channel": name, "rms_uv": round(rms, 4),
            "peak_to_peak_uv": round(float(np.ptp(row)), 4),
            "median_uv": round(float(np.median(row)), 4),
            "std_uv": round(float(np.std(row)), 4),
            "flat_step_fraction": round(float(np.mean(delta <= tolerance_uv)), 4),
            "line_50_fraction": round(noise50 / broad, 5) if broad and noise50 is not None else None,
            "line_60_fraction": round(noise60 / broad, 5) if broad and noise60 is not None else None,
        })
    return results


def hjorth_parameters(signal_uv: np.ndarray, sfreq: float) -> dict[str, float]:
    """Hjorth descriptors; mobility is reported in 1/s, not a diagnosis."""
    x = np.asarray(signal_uv, dtype=float)
    if x.ndim != 1 or x.size < 4 or not np.isfinite(sfreq) or sfreq <= 0 or not np.all(np.isfinite(x)):
        raise ValueError("Hjorth analysis requires >=4 finite samples and positive sfreq")
    dx = np.diff(x) * sfreq
    ddx = np.diff(dx) * sfreq
    activity = float(np.var(x))
    dvar = float(np.var(dx))
    ddvar = float(np.var(ddx))
    mobility = float(np.sqrt(dvar / activity)) if activity > 1e-20 else 0.0
    derivative_mobility = float(np.sqrt(ddvar / dvar)) if dvar > 1e-20 else 0.0
    complexity = float(derivative_mobility / mobility) if mobility > 1e-20 else 0.0
    return {"hjorth_activity_uv2": activity, "hjorth_mobility_per_s": mobility,
            "hjorth_complexity": complexity}


def time_frequency_psd(signal_uv: np.ndarray, sfreq: float, window_s: float = 2.0):
    """Spectrogram (Hz, segment center seconds, density µV²/Hz)."""
    from scipy.signal import spectrogram
    x = np.asarray(signal_uv, dtype=float)
    if x.ndim != 1 or x.size < 16 or not np.all(np.isfinite(x)):
        raise ValueError("A finite 1-D signal with >=16 samples is required")
    if not np.isfinite(sfreq) or not np.isfinite(window_s) or sfreq <= 0 or window_s <= 0:
        raise ValueError("Positive finite sampling frequency and window size required")
    nperseg = min(x.size, max(16, int(round(window_s * sfreq))))
    frequencies, times, density = spectrogram(
        x, fs=sfreq, window="hann", nperseg=nperseg, noverlap=nperseg // 2,
        detrend="constant", scaling="density", mode="psd")
    return frequencies, times, density


def pairwise_coherence(x_uv: np.ndarray, y_uv: np.ndarray, sfreq: float, window_s: float = 2.0):
    """Magnitude-squared coherence 0..1, NOT evidence of neural connectivity."""
    from scipy.signal import coherence
    x, y = np.asarray(x_uv, dtype=float), np.asarray(y_uv, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or len(x) != len(y) or len(x) < 16:
        raise ValueError("Both channels must be equal-length 1D arrays (>=16 samples)")
    if not np.isfinite(sfreq) or not np.isfinite(window_s) or sfreq <= 0 or window_s <= 0:
        raise ValueError("Positive finite sampling frequency and window size required")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("Coherence requires finite samples")
    nperseg = min(len(x), max(16, int(round(window_s * sfreq))))
    if len(x) < nperseg + (nperseg - nperseg // 2):
        raise ValueError("Coherence requires at least two overlapping Welch segments; shorten the window or use a longer recording")
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        raise ValueError("Coherence is undefined for a constant channel")
    freq, coh = coherence(x, y, fs=sfreq, window="hann", nperseg=nperseg,
                          noverlap=nperseg // 2)
    if not np.all(np.isfinite(coh)):
        raise ValueError("Coherence is undefined at frequencies with zero spectral power")
    return freq, np.clip(coh, 0, 1)


def emg_descriptors(signal_uv: np.ndarray, sfreq: float) -> dict[str, float]:
    """Descriptive EMG RMS, MAV, waveform length and median PSD frequency.

    These values depend on acquisition bandwidth and filtering. Median
    frequency *alone* is not a muscle-fatigue determination.
    """
    x = np.asarray(signal_uv, dtype=float)
    if x.ndim != 1 or x.size < 16 or not np.all(np.isfinite(x)) or not np.isfinite(sfreq) or sfreq <= 0:
        raise ValueError("EMG descriptors require a finite 1D signal and positive sfreq")
    freqs, psd = compute_psd(x[None, :], sfreq, window_s=min(2., len(x) / sfreq))
    density = psd[0]
    cumulative = np.cumsum((density[1:] + density[:-1]) / 2 * np.diff(freqs))
    total = float(cumulative[-1]) if cumulative.size else 0.0
    median_freq = float(np.interp(total / 2, cumulative, freqs[1:])) if total > 1e-20 else 0.0
    return {
        "emg_rms_uv": float(np.sqrt(np.mean(x**2))),
        "emg_mav_uv": float(np.mean(np.abs(x))),
        "emg_waveform_length_uv": float(np.sum(np.abs(np.diff(x)))),
        "emg_median_frequency_hz": median_freq,
    }
