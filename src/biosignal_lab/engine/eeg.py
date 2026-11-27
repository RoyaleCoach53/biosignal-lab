"""Scalp-signal transforms; coupling estimates do not establish neural sources."""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.signal import hilbert
from .model import Signal


def common_average_reference(signal: Signal):
    if signal.modality != "eeg" or len(signal.channels) < 2:
        raise ValueError("Common average reference requires >=2 EEG channels")
    return signal.transformed(
        signal.data - signal.data.mean(axis=0),
        "common_average_reference",
        reference="common_average",
        parameters={
            "channels": list(signal.channels),
            "bad_channels": "must be excluded by caller",
        },
    )


def bipolar_reference(signal: Signal, pairs):
    if signal.modality not in {"eeg", "eog", "ecg", "emg"}:
        raise ValueError("Bipolar reference requires electrical signals")
    pairs = tuple(tuple(pair) for pair in pairs)
    if not pairs or any(
        len(pair) != 2 or pair[0] == pair[1] or any(c not in signal.channels for c in pair)
        for pair in pairs
    ):
        raise ValueError("Bipolar pairs must contain distinct known channels")
    names = tuple(f"{a}-{b}" for a, b in pairs)
    data = np.array(
        [
            signal.data[signal.channels.index(a)] - signal.data[signal.channels.index(b)]
            for a, b in pairs
        ]
    )
    return signal.transformed(
        data, "bipolar_reference", parameters={"pairs": pairs}, channels=names, reference="bipolar"
    )


@dataclass(frozen=True)
class Epochs:
    data: np.ndarray  # epochs x channels x samples
    times: np.ndarray
    events: np.ndarray  # original sample indices, all retained; out-of-range fails
    channels: tuple[str, ...]
    sfreq: float
    unit: str
    reference: str | None
    metadata: dict

    def average(self):
        return Signal(
            self.data.mean(axis=0),
            self.sfreq,
            self.channels,
            self.metadata["modality"],
            self.unit,
            self.reference,
            {**self.metadata, "evoked_trials": len(self.events), "tmin_s": float(self.times[0])},
            (
                *self.metadata["source_history"],
                {
                    "operation": "event_average",
                    "parameters": {
                        "events": self.events.tolist(),
                        "tmin_s": float(self.times[0]),
                        "tmax_s": float(self.times[-1]),
                        "baseline_s": self.metadata["baseline_s"],
                    },
                },
            ),
        )


def epoch(signal: Signal, events, tmin=-0.2, tmax=0.8, baseline=None):
    """Inclusive endpoints rounded to nearest sample; no events silently dropped.

    Baseline endpoints are inclusive. Baseline is a time interval in seconds.
    """
    indices = np.asarray(events)
    if indices.ndim != 1 or not len(indices) or indices.dtype.kind not in "iu":
        raise ValueError("Events must be a nonempty 1-D integer sample index array")
    if not np.isfinite(tmin) or not np.isfinite(tmax) or tmin >= tmax:
        raise ValueError("Finite ordered epoch limits required")
    first, last = int(round(tmin * signal.sfreq)), int(round(tmax * signal.sfreq))
    if np.any(indices < 0) or np.any(indices >= signal.data.shape[1]):
        raise ValueError("Event sample indices must fit inside recording")
    if len(indices) * (last - first + 1) * len(signal.channels) > 100_000_000:
        raise ValueError("Epoch output exceeds resource limit")
    offsets = np.arange(first, last + 1)
    indices = indices.astype(np.int64)
    samples = indices[:, None] + offsets
    if samples.min() < 0 or samples.max() >= signal.data.shape[1]:
        raise ValueError("All epochs must fit inside recording; select valid events explicitly")
    data = np.moveaxis(signal.data[:, samples], 0, 1).copy()
    times = offsets / signal.sfreq
    if baseline is not None:
        if (
            len(baseline) != 2
            or not np.all(np.isfinite(baseline))
            or baseline[0] > baseline[1]
            or baseline[0] < times[0]
            or baseline[1] > times[-1]
        ):
            raise ValueError("Baseline interval must fit epoch")
        mask = (times >= baseline[0]) & (times <= baseline[1])
        if not mask.any():
            raise ValueError("Baseline contains no samples")
        data -= data[..., mask].mean(axis=-1, keepdims=True)
    return Epochs(
        data,
        times,
        indices.copy(),
        signal.channels,
        signal.sfreq,
        signal.unit,
        signal.reference,
        {
            "source_metadata": dict(signal.metadata),
            "source_history": signal.history,
            "baseline_s": baseline,
            "modality": signal.modality,
        },
    )


def phase_locking_value(signal: Signal):
    """Pairwise temporal PLV using Hilbert phase of caller-bandlimited signals.

    Volume conduction/common reference can cause coupling. Filter and exclude
    edge transients before calling. Constant signals are rejected.
    """
    if signal.data.shape[1] < 4 or np.any(np.ptp(signal.data, axis=-1) == 0):
        raise ValueError("PLV requires nonconstant channels and >=4 samples")
    phase = np.angle(hilbert(signal.data, axis=-1))
    complex_phase = np.exp(1j * phase)
    return np.clip(abs(complex_phase @ complex_phase.conj().T / phase.shape[1]), 0, 1)


def bad_channel_candidates(signal: Signal, flat_tolerance=0.0, scale_ratio=10.0):
    """Heuristic flatline/high-variance candidates, not artifact ground truth."""
    if (
        not np.isfinite(flat_tolerance)
        or flat_tolerance < 0
        or not np.isfinite(scale_ratio)
        or scale_ratio <= 1
    ):
        raise ValueError("Nonnegative flat tolerance and scale ratio >1 required")
    scales = signal.data.std(axis=-1)
    nonzero = scales[scales > 0]
    typical = np.median(nonzero) if len(nonzero) else 0
    return {
        name: [
            reason
            for reason, match in [
                ("flatline_candidate", np.ptp(row) <= flat_tolerance),
                ("high_variance_candidate", typical > 0 and scale > typical * scale_ratio),
            ]
            if match
        ]
        for name, row, scale in zip(signal.channels, signal.data, scales)
    }


def ica_remove(signal: Signal, *, exclude, n_components=None, random_state=42, max_iter=1000):
    """MNE FastICA with explicitly reviewed component indices.

    No component is automatically called an artifact. Filtering, rank, channel
    selection and sufficient data are caller responsibilities. Removing a
    component may remove desired activity; results require scientific review.
    """
    import mne

    if (
        signal.modality not in {"eeg", "eog"}
        or signal.unit not in {"V", "mV", "uV"}
        or len(signal.channels) < 2
    ):
        raise ValueError("ICA requires >=2 electrical EEG/EOG channels")
    if signal.data.shape[1] < 10 * len(signal.channels):
        raise ValueError("ICA requires at least 10 samples per channel")
    if not isinstance(max_iter, int) or not 1 <= max_iter <= 10000:
        raise ValueError("ICA iteration limit must be in 1..10000")
    if n_components is not None and (
        not isinstance(n_components, int) or not 1 <= n_components <= len(signal.channels)
    ):
        raise ValueError("ICA component count must fit channel count")
    excluded = list(exclude)
    if any(not isinstance(i, int) or i < 0 for i in excluded) or len(set(excluded)) != len(
        excluded
    ):
        raise ValueError("Excluded ICA components must be unique nonnegative integers")
    volts = signal.to_unit("V")
    raw = mne.io.RawArray(
        volts.data.copy(),
        mne.create_info(list(signal.channels), signal.sfreq, "eeg"),
        verbose="ERROR",
    )
    decomposition = mne.preprocessing.ICA(
        n_components=n_components, method="fastica", random_state=random_state, max_iter=max_iter
    )
    decomposition.fit(raw, verbose="ERROR")
    if any(i >= decomposition.n_components_ for i in excluded):
        raise ValueError("Excluded ICA component exceeds fitted rank")
    if decomposition.n_iter_ >= max_iter:
        raise ValueError("ICA reached iteration limit; do not silently accept unconverged solution")
    reconstructed = decomposition.apply(raw.copy(), exclude=excluded, verbose="ERROR").get_data()
    factor = {"V": 1.0, "mV": 1e3, "uV": 1e6}[signal.unit]
    parameters = {
        "method": "MNE FastICA",
        "mne_version": mne.__version__,
        "random_state": random_state,
        "n_components": int(decomposition.n_components_),
        "n_iter": int(decomposition.n_iter_),
        "exclude": excluded,
        "review_required": True,
    }
    return signal.transformed(
        reconstructed * factor, "ica_explicit_component_removal", parameters=parameters
    )


def handle_bad_channels(signal: Signal, bad_channels, *, method="drop", montage=None):
    """Explicitly drop or MNE-interpolate reviewed EEG bad channels.

    Interpolation uses spherical splines on a template or supplied montage and
    estimates missing scalp measurements; it does not recover true physiology.
    At least four reviewed good channels must remain for interpolation.
    """
    bad = tuple(bad_channels)
    if (
        signal.modality != "eeg"
        or not bad
        or len(set(bad)) != len(bad)
        or any(ch not in signal.channels for ch in bad)
    ):
        raise ValueError("Provide unique known EEG bad-channel labels")
    retained = [i for i, channel in enumerate(signal.channels) if channel not in bad]
    if method == "drop":
        if not retained:
            raise ValueError("Cannot drop every channel")
        return signal.transformed(
            signal.data[retained],
            "drop_reviewed_bad_channels",
            channels=tuple(signal.channels[i] for i in retained),
            parameters={"dropped": list(bad), "original_channels": list(signal.channels)},
        )
    if method != "interpolate" or len(retained) < 4:
        raise ValueError("Choose drop or interpolate; interpolation requires >=4 good channels")
    if signal.unit not in {"V", "mV", "uV"}:
        raise ValueError("EEG interpolation requires electrical amplitude units")
    import mne
    from .visualization import _montage_info

    info, montage_name = _montage_info(signal, montage)
    raw = mne.io.RawArray(signal.data.copy(), info, verbose="ERROR")
    raw.info["bads"] = list(bad)
    raw.interpolate_bads(
        reset_bads=False, mode="accurate", method={"eeg": "spline"}, verbose="ERROR"
    )
    return signal.transformed(
        raw.get_data(),
        "interpolate_reviewed_bad_channels",
        parameters={
            "interpolated": list(bad),
            "method": "MNE spherical spline",
            "mne_version": mne.__version__,
            "montage": montage_name,
            "origin": "auto sphere fit",
            "warning": "estimated scalp values; not recovered physiological ground truth",
        },
    )
