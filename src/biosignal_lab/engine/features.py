"""Descriptive EMG and peripheral-signal features; no diagnostic decisions."""

from __future__ import annotations
import hashlib
import numpy as np
from scipy import signal as sp
from scipy.integrate import cumulative_trapezoid, trapezoid
from .model import Signal
from .spectral import welch_psd


def emg_features(signal: Signal, threshold=0.0):
    """Thresholds use input amplitude units; slopes compare adjacent differences.

    Integrated EMG uses rectangular integration (sum |x| / sfreq). Features
    depend on filtering and acquisition; frequency changes do not prove fatigue.
    """
    if (
        signal.modality != "emg"
        or not np.isfinite(threshold)
        or threshold < 0
        or signal.data.shape[1] < 4
    ):
        raise ValueError("EMG with >=4 samples and nonnegative threshold required")
    x = signal.data
    differences = np.diff(x, axis=-1)
    frequencies, psd = welch_psd(signal, min(2.0, signal.duration_s))
    cumulative = cumulative_trapezoid(psd, frequencies, axis=-1, initial=0)
    total = cumulative[:, -1]
    mean = np.divide(
        trapezoid(psd * frequencies, frequencies, axis=-1),
        total,
        out=np.full(len(total), np.nan),
        where=total > 0,
    )
    median = [
        float(np.interp(t / 2, c, frequencies)) if t > 0 else None
        for c, t in zip(cumulative, total)
    ]
    return [
        {
            "channel": channel,
            "amplitude_unit": signal.unit,
            "rms": float(np.sqrt(np.mean(row**2))),
            "mean_absolute_value": float(np.mean(abs(row))),
            "waveform_length": float(sum(abs(diff))),
            "integrated_emg": float(sum(abs(row)) / signal.sfreq),
            "zero_crossings": int(
                np.count_nonzero((row[:-1] * row[1:] < 0) & (abs(diff) >= threshold))
            ),
            "slope_sign_changes": int(
                np.count_nonzero(
                    (diff[:-1] * diff[1:] < 0)
                    & (np.maximum(abs(diff[:-1]), abs(diff[1:])) >= threshold)
                )
            ),
            "median_frequency_hz": med,
            "mean_frequency_hz": float(avg) if np.isfinite(avg) else None,
        }
        for channel, row, diff, med, avg in zip(signal.channels, x, differences, median, mean)
    ]


def activation_intervals(signal: Signal, *, threshold, window_s=0.05, min_duration_s=0.05):
    """RMS envelope threshold crossing, not verified physiological onset.

    Windows are trailing for causal interpretation. First incomplete windows are
    excluded. Intervals use half-open sample boundaries and seconds.
    """
    if (
        signal.modality != "emg"
        or not np.isfinite(threshold)
        or threshold <= 0
        or not np.isfinite(window_s)
        or window_s <= 0
        or not np.isfinite(min_duration_s)
        or min_duration_s <= 0
    ):
        raise ValueError("Positive EMG envelope parameters required")
    count = max(1, int(round(window_s * signal.sfreq)))
    if count > signal.data.shape[1]:
        raise ValueError("Envelope window must fit recording")
    out = []
    for name, row in zip(signal.channels, signal.data):
        rms = np.sqrt(np.maximum(0, sp.lfilter(np.ones(count) / count, [1.0], row**2)))
        active = rms >= threshold
        active[: count - 1] = False
        edges = np.diff(np.r_[False, active, False].astype(int))
        for start, stop in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)):
            if (stop - start) / signal.sfreq >= min_duration_s:
                out.append(
                    {
                        "channel": name,
                        "start_s": start / signal.sfreq,
                        "stop_s": stop / signal.sfreq,
                        "kind": "rms_threshold_candidate",
                        "threshold": threshold,
                        "unit": signal.unit,
                    }
                )
    return out


def peak_intervals(signal: Signal, *, prominence, min_distance_s=0.3, polarity="positive"):
    """Configurable ECG/PPG/EOG peak candidates on explicitly preprocessed data.

    No automatic QRS, blink, arrhythmia or blood-pressure determination. Rate is
    only a descriptive reciprocal interval and requires reviewed peak identity.
    """
    if (
        signal.modality not in {"ecg", "ppg", "eog"}
        or not np.isfinite(prominence)
        or prominence <= 0
        or not np.isfinite(min_distance_s)
        or min_distance_s <= 0
        or polarity not in {"positive", "negative"}
    ):
        raise ValueError("ECG/PPG/EOG and positive peak settings required")
    out = []
    for channel, row in zip(signal.channels, signal.data):
        peaks, _ = sp.find_peaks(
            row if polarity == "positive" else -row,
            prominence=prominence,
            distance=max(1, int(np.ceil(min_distance_s * signal.sfreq))),
        )
        intervals = np.diff(peaks) / signal.sfreq
        out.append(
            {
                "channel": channel,
                "candidate_samples": peaks.tolist(),
                "candidate_times_s": (peaks / signal.sfreq).tolist(),
                "intervals_s": intervals.tolist(),
                "mean_rate_per_min": float(60 / intervals.mean()) if len(intervals) else None,
                "review_required": True,
            }
        )
    return out


def eda_components(signal: Signal, cutoff_hz=0.05):
    """Low-pass tonic approximation and residual, not deconvolved sudomotor activity.

    Cutoff and boundary effects materially change both components. Negative
    residual values are valid; no skin-conductance-response classification.
    """
    from .filters import FilterSpec, filter_signal

    if signal.modality != "eda" or signal.unit not in {"S", "uS"}:
        raise ValueError("EDA components require conductance units S or uS")
    tonic = filter_signal(signal, FilterSpec(kind="lowpass", cutoff=cutoff_hz, order=2))
    phasic = signal.transformed(
        signal.data - tonic.data,
        "eda_lowpass_residual",
        parameters={
            "cutoff_hz": cutoff_hz,
            "interpretation": "descriptive residual; no physiological source inference",
        },
    )
    return tonic, phasic


def adaptive_cancel(signal: Signal, reference: Signal, *, taps=16, step=0.1, epsilon=1e-8):
    """Normalized LMS cancellation; reference may also remove desired activity.

    Offline deterministic fit, zero weights/state. Return residual and final
    weights; this is not an automatic artifact classifier.
    """
    if (
        signal.sfreq != reference.sfreq
        or signal.data.shape != reference.data.shape
        or signal.unit != reference.unit
    ):
        raise ValueError("Adaptive reference must match shape, sfreq and units")
    if (
        not isinstance(taps, int)
        or not 1 <= taps <= min(4096, signal.data.shape[1])
        or not np.isfinite(step)
        or not 0 < step < 2
        or not np.isfinite(epsilon)
        or epsilon <= 0
    ):
        raise ValueError("Invalid NLMS taps, step or epsilon")
    weights = np.zeros((len(signal.channels), taps))
    output = signal.data.copy()
    padded = np.pad(reference.data, ((0, 0), (taps - 1, 0)))
    for n in range(signal.data.shape[1]):
        vector = padded[:, n : n + taps][:, ::-1]
        estimate = np.sum(weights * vector, axis=1)
        error = signal.data[:, n] - estimate
        weights += (
            step * error[:, None] * vector / (epsilon + np.sum(vector**2, axis=1, keepdims=True))
        )
        output[:, n] = error
    return signal.transformed(
        output,
        "nlms_reference_cancel",
        parameters={
            "taps": taps,
            "step": step,
            "epsilon": epsilon,
            "reference_input": {
                "data_sha256": hashlib.sha256(reference.data.tobytes(order="C")).hexdigest(),
                "shape": list(reference.data.shape),
                "dtype": reference.data.dtype.str,
                "sfreq": reference.sfreq,
                "unit": reference.unit,
                "modality": reference.modality,
                "reference": reference.reference,
                "metadata": dict(reference.metadata),
                "history": reference.history,
                "channel_mapping": [
                    {"target": target, "reference": ref}
                    for target, ref in zip(signal.channels, reference.channels)
                ],
                "mapping_policy": "positional; acquisition time synchronization is caller responsibility",
            },
            "warning": "desired signal correlated with reference may be removed",
        },
    ), weights
