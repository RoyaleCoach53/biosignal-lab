"""Studio adapters for the real additive scientific engine."""
from __future__ import annotations

import math

from ..engine import Signal, FilterSpec, filter_signal, resample_signal, welch_psd, common_average_reference
from .nodes import _parameters, _empty, _psd_validate
from .runtime import Definition, Port, WorkflowError


def _filter_validate(p):
    _parameters({k: v for k, v in p.items() if k != "cutoff"},
                {"family": ("butter", "cheby1", "cheby2", "bessel", "ellip", "fir"),
                 "kind": ("lowpass", "highpass", "bandpass", "bandstop", "notch"),
                 "order": "integer", "phase": ("zero", "causal"), "ripple_db": "number",
                 "attenuation_db": "number", "quality": "number"})
    if "cutoff" in p:
        values = p["cutoff"] if isinstance(p["cutoff"], list) else [p["cutoff"]]
        if not 1 <= len(values) <= 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in values):
            raise ValueError("cutoff must be one or two positive finite frequencies")
    if not 1 <= p.get("order", 4) <= 1001:
        raise ValueError("Studio bounds filter order/tap count to 1..1001")


def _resample_validate(p):
    _parameters(p, {"sfreq": "number"})
    if "sfreq" not in p or not 0 < p["sfreq"] <= 100_000:
        raise ValueError("Resample requires sfreq in (0, 100000]")


def _resample(i, p, c):
    signal = i["signal"]
    expected = math.ceil(signal.data.shape[1] * p["sfreq"] / signal.sfreq) * len(signal.channels)
    if expected > c.limits.max_signal_values:
        raise WorkflowError("Resampling exceeds sample-value limit before allocation")
    return {"out": resample_signal(signal, p["sfreq"])}


def _psd(i, p, c):
    signal = i["signal"]
    frequencies, power = welch_psd(signal, p.get("window_s", 2))
    return {"out": {"frequencies": frequencies, "power": power, "sfreq": signal.sfreq,
                    "unit": f"{signal.unit}^2/Hz", "channels": signal.channels,
                    "modality": signal.modality}}


def register_engine_nodes(registry):
    signal = Port("signal")
    for definition in [
        Definition("engine_signal", {"recording": Port("recording", unit="uV")}, {"out": signal},
                   lambda i, p, c: {"out": Signal.from_recording(i["recording"])}, _empty,
                   description="Convert legacy recording to metadata-preserving engine Signal"),
        Definition("filter", {"signal": signal}, {"out": signal},
                   lambda i, p, c: {"out": filter_signal(i["signal"], FilterSpec(**p))}, _filter_validate,
                   description="Validated Butterworth/Chebyshev/Bessel/elliptic/FIR filtering"),
        Definition("resample", {"signal": signal}, {"out": signal}, _resample, _resample_validate,
                   description="Polyphase resampling with anti-aliasing"),
        Definition("common_reference", {"signal": Port("signal", modality="eeg")}, {"out": signal},
                   lambda i, p, c: {"out": common_average_reference(i["signal"])}, _empty,
                   description="EEG common-average reference with recorded provenance"),
        Definition("engine_psd", {"signal": signal}, {"out": Port("spectrum")}, _psd, _psd_validate,
                   description="Engine Welch PSD retaining physical unit labels"),
        Definition("signal_metadata", {"signal": signal}, {"out": Port("json")},
                   lambda i, p, c: {"out": {"sfreq": i["signal"].sfreq,
                                             "channels": list(i["signal"].channels),
                                             "modality": i["signal"].modality, "unit": i["signal"].unit,
                                             "reference": i["signal"].reference,
                                             "metadata": dict(i["signal"].metadata),
                                             "history": list(i["signal"].history)}}, _empty,
                   description="Inspect physical units, reference and complete engine transformation history"),
    ]:
        registry.register(definition, trusted=True)
