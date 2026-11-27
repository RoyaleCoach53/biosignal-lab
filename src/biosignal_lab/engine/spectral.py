"""Spectral estimates in explicit input-unit squared per Hz."""

from __future__ import annotations
import numpy as np
from scipy import signal as sp
from scipy.integrate import trapezoid
from .model import Signal


def _checked(*arrays):
    if any(not np.all(np.isfinite(array)) for array in arrays):
        raise ValueError("Numerical overflow in spectral calculation; rescale input units")
    return arrays


def _segment(signal, window_s):
    if not np.isfinite(window_s) or window_s <= 0:
        raise ValueError("Window must be finite and positive")
    n = int(round(window_s * signal.sfreq))
    if not 4 <= n <= signal.data.shape[1]:
        raise ValueError("Window must contain >=4 samples and fit within recording")
    return n


def welch_psd(signal: Signal, window_s=2.0):
    n = _segment(signal, window_s)
    return _checked(
        *sp.welch(
            signal.data,
            fs=signal.sfreq,
            window="hann",
            nperseg=n,
            noverlap=n // 2,
            detrend="constant",
            scaling="density",
            axis=-1,
        )
    )


def fft_spectrum(signal: Signal):
    """One-sided amplitudes, input units; rectangular window, no detrending."""
    n = signal.data.shape[1]
    amplitude = abs(np.fft.rfft(signal.data, axis=-1)) / n
    amplitude[:, 1 : -1 if n % 2 == 0 else None] *= 2
    return _checked(np.fft.rfftfreq(n, 1 / signal.sfreq), amplitude)


def stft(signal: Signal, window_s=2.0):
    """Complex STFT (input units), without boundary extension or tail padding."""
    n = _segment(signal, window_s)
    return _checked(
        *sp.stft(
            signal.data,
            fs=signal.sfreq,
            window="hann",
            nperseg=n,
            noverlap=n // 2,
            boundary=None,
            padded=False,
            axis=-1,
        )
    )


def spectrogram(signal: Signal, window_s=2.0):
    n = _segment(signal, window_s)
    return _checked(
        *sp.spectrogram(
            signal.data,
            fs=signal.sfreq,
            window="hann",
            nperseg=n,
            noverlap=n // 2,
            detrend="constant",
            scaling="density",
            axis=-1,
        )
    )


def multitaper_psd(signal: Signal, time_bandwidth=3.0, n_tapers=None):
    """Equal-weight DPSS periodograms; no adaptive weighting or jackknife CI.

    Bandwidth is approximately 2*NW/duration. Constant channel means are removed.
    """
    n = signal.data.shape[1]
    if not np.isfinite(time_bandwidth) or not 1 <= time_bandwidth < n / 2:
        raise ValueError("Time-bandwidth must be >=1 and <n_samples/2")
    count = max(1, int(2 * time_bandwidth) - 1) if n_tapers is None else n_tapers
    if (
        isinstance(count, bool)
        or not isinstance(count, int)
        or not 1 <= count <= min(n, int(2 * time_bandwidth))
    ):
        raise ValueError("Taper count must be positive and <=2*NW")
    if count * (n + signal.data.size) > 100_000_000:
        raise ValueError("Multitaper output exceeds resource limit")
    windows = sp.windows.dpss(n, time_bandwidth, Kmax=count, sym=False)
    x = signal.data - signal.data.mean(axis=-1, keepdims=True)
    coefficients = np.fft.rfft(x[:, None, :] * windows[None, :, :], axis=-1)
    power = abs(coefficients) ** 2 / (signal.sfreq * (windows**2).sum(axis=-1)[None, :, None])
    power[..., 1 : -1 if n % 2 == 0 else None] *= 2
    return _checked(np.fft.rfftfreq(n, 1 / signal.sfreq), power.mean(axis=1))


def spectral_entropy(power, *, normalized=True):
    power = np.asarray(power, dtype=float)
    if (
        power.ndim < 1
        or power.shape[-1] < 2
        or not np.all(np.isfinite(power))
        or np.any(power < 0)
        or np.any(power.max(axis=-1) <= 0)
    ):
        raise ValueError("Entropy requires nonnegative finite power with positive total")
    power = power / power.max(axis=-1, keepdims=True)
    probabilities = power / power.sum(axis=-1, keepdims=True)
    logs = np.zeros_like(probabilities)
    np.log2(probabilities, out=logs, where=probabilities > 0)
    out = -(probabilities * logs).sum(axis=-1)
    return out / np.log2(power.shape[-1]) if normalized else out


def integrate_band(frequencies, power, low, high):
    f, p = np.asarray(frequencies, dtype=float), np.asarray(power, dtype=float)
    if (
        p.ndim < 1
        or f.ndim != 1
        or f.size < 2
        or not np.all(np.isfinite(f))
        or not np.all(np.diff(f) > 0)
        or p.shape[-1] != f.size
        or not np.all(np.isfinite(p))
        or np.any(p < 0)
    ):
        raise ValueError("Ordered frequencies and matching finite nonnegative power required")
    if not np.isfinite(low) or not np.isfinite(high) or not f[0] <= low < high <= f[-1]:
        raise ValueError("Entire requested band must lie within measured spectral support")
    grid = np.r_[low, f[(f > low) & (f < high)], high]
    rows = p.reshape(-1, f.size)
    integrated = np.array([trapezoid(np.interp(grid, f, row), grid) for row in rows])
    return _checked(integrated.reshape(p.shape[:-1]))[0]


def wavelet_transform(signal: Signal, *, wavelet="morl", frequencies=None):
    """PyWavelets CWT coefficients, not a calibrated PSD. Edge effects remain."""
    try:
        import pywt
    except ImportError as exc:
        raise ImportError("Install PyWavelets for wavelet analysis") from exc
    f = np.asarray(
        frequencies if frequencies is not None else np.geomspace(1, signal.sfreq / 3, 32),
        dtype=float,
    )
    if (
        f.ndim != 1
        or not len(f)
        or not np.all(np.isfinite(f))
        or np.any(f <= 0)
        or np.any(f >= signal.sfreq / 2)
    ):
        raise ValueError("Wavelet frequencies must lie strictly inside Nyquist")
    if f.size * signal.data.size > 100_000_000:
        raise ValueError("Wavelet output exceeds resource limit")
    scales = pywt.central_frequency(wavelet) * signal.sfreq / f
    if np.any(scales > signal.data.shape[1]):
        raise ValueError("Requested wavelet scale exceeds recording support")
    coefficients, actual = pywt.cwt(
        signal.data, scales, wavelet, sampling_period=1 / signal.sfreq, axis=-1
    )
    return _checked(actual, coefficients)


def discrete_wavelet(signal: Signal, *, wavelet="db4", level=None):
    try:
        import pywt
    except ImportError as exc:
        raise ImportError("Install PyWavelets for wavelet analysis") from exc
    maximum = pywt.dwt_max_level(signal.data.shape[1], pywt.Wavelet(wavelet).dec_len)
    if level is not None and (not isinstance(level, int) or not 1 <= level <= maximum):
        raise ValueError("Wavelet level exceeds boundary-safe decomposition limit")
    return list(
        _checked(*pywt.wavedec(signal.data, wavelet, mode="symmetric", level=level, axis=-1))
    )


def band_features(signal: Signal, *, bands=None, window_s=2.0, reference_band=(0.5, 45.0)):
    """Absolute/relative observed spectral power with explicit coverage and units.

    Incomplete bands and unavailable normalization ranges return None, never
    measured zero. Relative values require positive fully observed reference power.
    """
    from ..models import EEG_BANDS

    if bands is None:
        if signal.modality != "eeg":
            raise ValueError("Specify justified frequency bands for non-EEG signals")
        bands = EEG_BANDS
    if (
        not isinstance(bands, dict)
        or not bands
        or any(not isinstance(name, str) or not name for name in bands)
    ):
        raise ValueError("Bands must be a nonempty mapping from labels to frequency pairs")
    for edges in [*bands.values(), reference_band]:
        if len(edges) != 2 or not np.all(np.isfinite(edges)) or not 0 <= edges[0] < edges[1]:
            raise ValueError("Finite ordered nonnegative band boundaries required")
    frequencies, power = welch_psd(signal, window_s)
    maximum = float(frequencies[-1])
    complete_reference = reference_band[1] <= maximum
    totals = integrate_band(frequencies, power, *reference_band) if complete_reference else None
    output = []
    for i, channel in enumerate(signal.channels):
        descriptions = {}
        for name, (low, high) in bands.items():
            coverage = max(0.0, min(high, maximum) - low) / (high - low)
            absolute = (
                float(integrate_band(frequencies, power[i], low, high)) if coverage >= 1.0 else None
            )
            relative = (
                absolute / float(totals[i])
                if absolute is not None and totals is not None and totals[i] > 0
                else None
            )
            descriptions[name] = {
                "absolute": absolute,
                "relative": relative,
                "coverage": coverage,
                "range_hz": [low, high],
            }
        entropy = float(spectral_entropy(power[i])) if np.any(power[i] > 0) else None
        output.append(
            {
                "channel": channel,
                "power_unit": f"{signal.unit}^2",
                "bands": descriptions,
                "reference_range_hz": list(reference_band),
                "reference_power": float(totals[i]) if totals is not None else None,
                "spectral_entropy_normalized": entropy,
                "maximum_observed_frequency_hz": maximum,
            }
        )
    return output


def coherence_matrix(signal: Signal, window_s=2.0):
    """Pairwise magnitude-squared coherence, frequency x channel x channel.

    At least two overlapping Welch segments and nonconstant channels are required.
    Common reference/volume conduction can cause coupling without neural interaction.
    """
    n = _segment(signal, window_s)
    count = len(signal.channels)
    if count < 2:
        raise ValueError("Pairwise coherence requires at least two channels")
    if signal.data.shape[1] < n + (n - n // 2) or np.any(np.ptp(signal.data, axis=-1) == 0):
        raise ValueError("Coherence requires >=2 Welch segments and nonconstant channels")
    if (n // 2 + 1) * count * count > 20_000_000:
        raise ValueError("Coherence matrix exceeds resource limit")
    frequencies = np.fft.rfftfreq(n, 1 / signal.sfreq)
    output = np.ones((len(frequencies), count, count))
    for i in range(count):
        for j in range(i + 1, count):
            found, coupling = sp.coherence(
                signal.data[i],
                signal.data[j],
                fs=signal.sfreq,
                window="hann",
                nperseg=n,
                noverlap=n // 2,
                detrend="constant",
            )
            _checked(found, coupling)
            output[:, i, j] = output[:, j, i] = np.clip(coupling, 0, 1)
    return frequencies, output
