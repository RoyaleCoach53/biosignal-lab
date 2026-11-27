"""Validated digital filters; offline padding and causal state are explicit."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
import numpy as np
from scipy import signal as sp
from .model import Signal


@dataclass(frozen=True)
class FilterSpec:
    family: str = "butter"
    kind: str = "bandpass"
    cutoff: float | tuple[float, float] = (1.0, 40.0)
    order: int = 4
    phase: str = "zero"
    ripple_db: float = 1.0
    attenuation_db: float = 40.0
    quality: float = 30.0

    def coefficients(self, sfreq):
        if not np.isfinite(sfreq) or sfreq <= 0 or self.phase not in {"zero", "causal"}:
            raise ValueError("Positive sfreq and zero/causal phase required")
        if (
            isinstance(self.order, bool)
            or not isinstance(self.order, int)
            or not 1 <= self.order <= 10001
        ):
            raise ValueError("Filter order/tap count must be an integer in 1..10001")
        if self.kind not in {"lowpass", "highpass", "bandpass", "bandstop", "notch"}:
            raise ValueError("Unsupported filter kind")
        cutoff = np.atleast_1d(self.cutoff).astype(float)
        expected = 2 if self.kind in {"bandpass", "bandstop"} else 1
        if (
            len(cutoff) != expected
            or not np.all(np.isfinite(cutoff))
            or np.any(cutoff <= 0)
            or np.any(cutoff >= sfreq / 2)
            or (expected == 2 and cutoff[0] >= cutoff[1])
        ):
            raise ValueError("Ordered cutoff frequencies must lie strictly inside Nyquist")
        for value in (self.ripple_db, self.attenuation_db, self.quality):
            if not np.isfinite(value) or value <= 0:
                raise ValueError("Ripple, attenuation and quality must be positive")
        if self.kind == "notch":
            b, a = sp.iirnotch(cutoff[0], self.quality, fs=sfreq)
            return "sos", sp.tf2sos(b, a)
        if self.family == "fir":
            if self.order < 3 or self.order % 2 == 0:
                raise ValueError("FIR order denotes an odd tap count >=3")
            return "fir", sp.firwin(self.order, cutoff, pass_zero=self.kind, fs=sfreq)
        if self.family not in {"butter", "cheby1", "cheby2", "bessel", "ellip"} or self.order > 20:
            raise ValueError("Supported IIR families require order <=20")
        return "sos", sp.iirfilter(
            self.order,
            float(cutoff[0]) if expected == 1 else cutoff,
            rp=self.ripple_db,
            rs=self.attenuation_db,
            btype=self.kind,
            ftype=self.family,
            fs=sfreq,
            output="sos",
        )


def filter_signal(signal: Signal, spec: FilterSpec) -> Signal:
    form, coefficients = spec.coefficients(signal.sfreq)
    if form == "sos":
        # Same explicit odd-extension policy as SciPy; always record it.
        pad = 3 * (
            2 * len(coefficients)
            + 1
            - min((coefficients[:, 2] == 0).sum(), (coefficients[:, 5] == 0).sum())
        )
        if spec.phase == "zero":
            if signal.data.shape[1] <= pad:
                raise ValueError(f"Zero-phase filter requires more than {pad} samples")
            out = sp.sosfiltfilt(coefficients, signal.data, axis=-1, padtype="odd", padlen=pad)
        else:
            out = sp.sosfilt(coefficients, signal.data, axis=-1)
    else:
        pad = 3 * len(coefficients)
        if spec.phase == "zero":
            if signal.data.shape[1] <= pad:
                raise ValueError(f"Zero-phase FIR requires more than {pad} samples")
            out = sp.filtfilt(coefficients, [1.0], signal.data, axis=-1, padtype="odd", padlen=pad)
        else:
            out = sp.lfilter(coefficients, [1.0], signal.data, axis=-1)
    return signal.transformed(
        out,
        "filter",
        parameters={
            **asdict(spec),
            "padding": "odd" if spec.phase == "zero" else "none; zero initial state",
            "pad_samples": int(pad) if spec.phase == "zero" else 0,
            "note": "Zero phase is acausal and squares the single-pass magnitude response; edge transients remain.",
        },
    )


class StreamingFilter:
    """Causal filter whose zero-initialized state persists across sample chunks.

    One consumer must own an instance. Reset explicitly after discontinuities.
    """

    def __init__(self, spec: FilterSpec, sfreq: float, n_channels: int):
        if spec.phase != "causal" or not isinstance(n_channels, int) or n_channels < 1:
            raise ValueError("Streaming requires causal phase and positive channel count")
        self.form, self.coefficients = spec.coefficients(sfreq)
        self.n_channels = n_channels
        self.reset()

    def reset(self):
        if self.form == "sos":
            self.state = np.zeros((len(self.coefficients), self.n_channels, 2))
        else:
            self.state = np.zeros((self.n_channels, len(self.coefficients) - 1))

    def process(self, data):
        data = np.asarray(data, dtype=float)
        if (
            data.ndim != 2
            or data.shape[0] != self.n_channels
            or data.shape[1] < 1
            or not np.all(np.isfinite(data))
        ):
            raise ValueError("Chunk must be finite channels x samples with matching channels")
        if self.form == "sos":
            out, state = sp.sosfilt(self.coefficients, data, axis=-1, zi=self.state)
        else:
            out, state = sp.lfilter(self.coefficients, [1.0], data, axis=-1, zi=self.state)
        if not np.all(np.isfinite(out)):
            raise ValueError("Filter produced nonfinite output; state was not advanced")
        self.state = state
        return out


def resample_signal(signal: Signal, new_sfreq: float) -> Signal:
    if not np.isfinite(new_sfreq) or new_sfreq <= 0:
        raise ValueError("New sampling frequency must be finite and positive")
    ratio = Fraction(float(new_sfreq / signal.sfreq)).limit_denominator(10000)
    if not np.isclose(float(ratio), new_sfreq / signal.sfreq, rtol=1e-10, atol=0):
        raise ValueError("Sampling ratio cannot be represented accurately within resource limit")
    if max(ratio.numerator, ratio.denominator) > 10000:
        raise ValueError("Resampling ratio exceeds resource limit")
    output_samples = int(np.ceil(signal.data.shape[1] * float(ratio)))
    if output_samples * signal.data.shape[0] > 100_000_000:
        raise ValueError("Resampling output exceeds resource limit")
    out = sp.resample_poly(signal.data, ratio.numerator, ratio.denominator, axis=-1, padtype="line")
    return signal.transformed(
        out,
        "resample_poly",
        parameters={
            "up": ratio.numerator,
            "down": ratio.denominator,
            "anti_alias": "Kaiser FIR beta=5.0",
            "padding": "line",
            "edge_transients": True,
        },
        sfreq=float(new_sfreq),
    )


def detrend_signal(signal: Signal, kind="linear"):
    if kind not in {"linear", "constant"}:
        raise ValueError("Detrend kind must be linear or constant")
    return signal.transformed(
        sp.detrend(signal.data, type=kind, axis=-1), "detrend", parameters={"kind": kind}
    )


def normalize_signal(signal: Signal, method="zscore"):
    if method == "zscore":
        scale = signal.data.std(axis=-1, keepdims=True)
        center = signal.data.mean(axis=-1, keepdims=True)
    elif method == "robust":
        center = np.median(signal.data, axis=-1, keepdims=True)
        scale = 1.4826 * np.median(np.abs(signal.data - center), axis=-1, keepdims=True)
    else:
        raise ValueError("Normalization method must be zscore or robust")
    if not np.all(np.isfinite(scale)) or not np.all(np.isfinite(center)):
        raise ValueError("Normalization overflow; rescale input units")
    if np.any(scale <= 0):
        raise ValueError("Cannot normalize channels with zero dispersion")
    return signal.transformed(
        (signal.data - center) / scale,
        "normalize",
        parameters={"method": method, "original_unit": signal.unit},
        unit="a.u.",
    )


def repair_missing(
    data,
    sfreq,
    channels,
    *,
    modality="eeg",
    unit="uV",
    max_gap_s=0.1,
    max_missing_fraction=0.05,
    reference=None,
    metadata=None,
):
    """Bounded interior linear interpolation before constructing finite Signal.

    Never extrapolate edges or accept infinite values. Interpolation does not
    recover physiological information and its provenance is retained.
    """
    from ..preprocessing import fill_short_gaps

    data = np.asarray(data, dtype=float)
    if data.ndim != 2 or min(data.shape) < 1 or np.any(np.isinf(data)):
        raise ValueError("Finite or NaN channel-by-sample input required")
    if (
        not np.isfinite(sfreq)
        or sfreq <= 0
        or not np.isfinite(max_gap_s)
        or max_gap_s < 0
        or not np.isfinite(max_missing_fraction)
        or not 0 <= max_missing_fraction <= 1
    ):
        raise ValueError("Invalid interpolation limits")
    filled, warnings = fill_short_gaps(data, max_missing_fraction, int(np.floor(sfreq * max_gap_s)))
    return Signal(
        filled,
        sfreq,
        tuple(channels),
        modality,
        unit,
        reference,
        metadata or {},
        (
            {
                "operation": "interior_linear_interpolation",
                "parameters": {
                    "max_gap_s": max_gap_s,
                    "max_missing_fraction": max_missing_fraction,
                    "warnings": warnings,
                },
            },
        ),
    )
