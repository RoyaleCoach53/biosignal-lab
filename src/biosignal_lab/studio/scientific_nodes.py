"""Bounded adapters to verified engine transforms, never algorithm placeholders."""
from __future__ import annotations

from importlib.util import find_spec
from dataclasses import replace
import math

import numpy as np

from .. import engine
from .nodes import _parameters, _empty, _psd_validate
from .runtime import Definition, Port, WorkflowError


def _json_budget(context, count):
    # Python lists/JSON are substantially larger than native float arrays.
    if count > min(context.limits.max_signal_values, 200_000):
        raise WorkflowError("Scientific JSON output exceeds 200000-value budget; shorten signal or reduce channels/frequencies")


def _base(signal):
    return {"channels": list(signal.channels), "sfreq": signal.sfreq,
            "modality": signal.modality, "reference": signal.reference,
            "source_history": list(signal.history)}


def _fft(i, p, c):
    signal = i["signal"]
    _json_budget(c, len(signal.channels) * (signal.data.shape[1] // 2 + 1))
    frequencies, amplitude = engine.fft_spectrum(signal)
    return {"out": {**_base(signal), "representation": "one-sided FFT amplitude",
                    "frequencies_hz": frequencies.tolist(), "amplitude": amplitude.tolist(),
                    "unit": signal.unit, "window": "rectangular", "detrending": "none"}}


def _time_frequency(i, p, c, *, density):
    signal = i["signal"]
    window = p.get("window_s", 2)
    n = round(window * signal.sfreq)
    if not 4 <= n <= signal.data.shape[1]:
        raise ValueError("Time-frequency window must contain >=4 samples and fit recording")
    frames = 1 + (signal.data.shape[1] - n) // (n - n // 2)
    _json_budget(c, (1 if density else 2) * len(signal.channels) * (n // 2 + 1) * frames)
    frequencies, times, coefficients = (engine.spectrogram if density else engine.stft)(signal, window)
    output = {**_base(signal), "frequencies_hz": frequencies.tolist(), "times_s": times.tolist(),
              "window": "hann", "noverlap_samples": n // 2, "nperseg_samples": n,
              "shape_order": ["channel", "frequency", "time"]}
    if density:
        output.update(representation="spectrogram PSD", power=coefficients.tolist(), unit=f"{signal.unit}^2/Hz",
                      detrending="constant per segment")
    else:
        output.update(representation="complex STFT coefficients; spectrum scaling, not calibrated PSD",
                      real=coefficients.real.tolist(), imaginary=coefficients.imag.tolist(), unit=signal.unit,
                      detrending="none", boundary="none", padded=False)
    return {"out": output}


def _multitaper_validate(p):
    _parameters(p, {"time_bandwidth": "number", "n_tapers": "integer"})
    if not 1 <= p.get("time_bandwidth", 3) <= 16 or not 1 <= p.get("n_tapers", 1) <= 32:
        raise ValueError("Use time_bandwidth in [1,16] and taper count in [1,32]")


def _multitaper(i, p, c):
    signal = i["signal"]
    count = p.get("n_tapers", max(1, int(2 * p.get("time_bandwidth", 3)) - 1))
    if count * (signal.data.shape[1] + signal.data.size) > c.limits.max_signal_values:
        raise WorkflowError("Multitaper intermediate allocation exceeds configured value limit")
    frequencies, power = engine.multitaper_psd(signal, **p)
    return {"out": {"frequencies": frequencies, "power": power, "unit": f"{signal.unit}^2/Hz",
                    "sfreq": signal.sfreq, "channels": signal.channels, "modality": signal.modality}}


def _entropy_validate(p):
    _parameters(p, {"normalized": "boolean"})


def _entropy(i, p, c):
    spectrum = i["spectrum"]
    values = engine.spectral_entropy(spectrum["power"], normalized=p.get("normalized", True))
    return {"out": {"channels": list(spectrum["channels"]), "entropy": values.tolist(),
                    "normalized": p.get("normalized", True), "unit": "dimensionless" if p.get("normalized", True) else "bits",
                    "scope": "Entropy of the measured discrete spectral bins; depends on estimator and frequency support."}}


def _band_validate(p):
    _parameters(p, {"low_hz": "number", "high_hz": "number"})
    if not {"low_hz", "high_hz"} <= set(p) or not 0 <= p["low_hz"] < p["high_hz"]:
        raise ValueError("Band integration requires ordered nonnegative low_hz and high_hz")


def _band(i, p, c):
    spectrum = i["spectrum"]
    values = engine.integrate_band(spectrum["frequencies"], spectrum["power"], p["low_hz"], p["high_hz"])
    return {"out": {"channels": list(spectrum["channels"]), "power": values.tolist(),
                    "low_hz": p["low_hz"], "high_hz": p["high_hz"],
                    "unit": spectrum["unit"].removesuffix("/Hz"),
                    "method": "trapezoidal integration with interpolated band endpoints"}}


def _bipolar_validate(p):
    _parameters({k: v for k, v in p.items() if k != "pairs"}, {})
    pairs = p.get("pairs")
    if (not isinstance(pairs, list) or not 1 <= len(pairs) <= 128
            or any(not isinstance(pair, list) or len(pair) != 2
                   or any(not isinstance(label, str) or not label for label in pair) for pair in pairs)):
        raise ValueError("pairs must contain 1..128 explicit two-channel label lists")


def _bipolar(i, p, c):
    if len(p["pairs"]) * i["signal"].data.shape[1] > c.limits.max_signal_values:
        raise WorkflowError("Bipolar output exceeds value limit before allocation")
    return {"out": engine.bipolar_reference(i["signal"], p["pairs"])}


def _plv(i, p, c):
    signal = i["signal"]
    _json_budget(c, len(signal.channels) ** 2)
    return {"out": {"channels": list(signal.channels), "matrix": engine.phase_locking_value(signal).tolist(),
                    "unit": "dimensionless", "method": "Hilbert phase temporal PLV",
                    "reference": signal.reference,
                    "scope": "Caller must band-limit data and exclude filter edges. Volume conduction/common reference can induce coupling. Scalp coupling is not inferred neural connectivity."}}


def _bad_validate(p):
    _parameters(p, {"flat_tolerance": "number", "scale_ratio": "number"})
    if p.get("flat_tolerance", 0) < 0 or p.get("scale_ratio", 10) <= 1:
        raise ValueError("Use nonnegative flat_tolerance and scale_ratio >1")


def _epochs_validate(p):
    _parameters({k: v for k, v in p.items() if k not in {"events", "baseline"}},
                {"tmin": "number", "tmax": "number"})
    if not isinstance(p.get("events"), list) or not 1 <= len(p["events"]) <= 1000 or any(type(event) is not int or event < 0 for event in p["events"]):
        raise ValueError("events must contain 1..1000 nonnegative integer sample indices")
    if not p.get("tmin", -.2) < p.get("tmax", .8):
        raise ValueError("tmin must precede tmax")
    baseline = p.get("baseline")
    if baseline is not None and (not isinstance(baseline, list) or len(baseline) != 2
                                 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in baseline)):
        raise ValueError("baseline must be null or two finite time limits")


def _epochs(i, p, c):
    signal = i["signal"]
    count = round(p.get("tmax", .8) * signal.sfreq) - round(p.get("tmin", -.2) * signal.sfreq) + 1
    if len(p["events"]) * len(signal.channels) * count > c.limits.max_signal_values:
        raise WorkflowError("Epoch allocation exceeds configured value limit")
    return {"out": engine.epoch(signal, **p)}


def _epoch_info(i, p, c):
    epochs = i["epochs"]
    return {"out": {"events": epochs.events.tolist(), "shape": list(epochs.data.shape),
                    "tmin_s": float(epochs.times[0]), "tmax_s": float(epochs.times[-1]),
                    "sfreq": epochs.sfreq, "channels": list(epochs.channels), "unit": epochs.unit,
                    "reference": epochs.reference, "metadata": epochs.metadata}}


def _ica_validate(p):
    _parameters({k: v for k, v in p.items() if k != "exclude"},
                {"reviewed": "boolean", "n_components": "integer", "random_state": "integer", "max_iter": "integer"})
    exclude = p.get("exclude")
    if p.get("reviewed") is not True or not isinstance(exclude, list) or len(exclude) > 32 or any(type(item) is not int or item < 0 for item in exclude):
        raise ValueError("ICA requires reviewed=true and explicit nonnegative excluded component indices (empty list reconstructs without removal)")
    if not 1 <= p.get("n_components", 1) <= 32 or not 1 <= p.get("max_iter", 200) <= 1000 or p.get("random_state", 42) < 0:
        raise ValueError("Use 1..32 ICA components, 1..1000 iterations and nonnegative seed")


def _ica(i, p, c):
    signal = i["signal"]
    if signal.data.size > min(c.limits.max_signal_values, 500_000) or len(signal.channels) > 32:
        raise WorkflowError("Studio ICA is bounded to 500000 input values and 32 channels")
    parameters = {"max_iter": 200} | {k: v for k, v in p.items() if k != "reviewed"}
    return {"out": engine.ica_remove(signal, **parameters)}


def _emg_validate(p):
    _parameters(p, {"threshold": "number"})
    if p.get("threshold", 0) < 0:
        raise ValueError("EMG threshold must be nonnegative and uses input amplitude units")


def _activation_validate(p):
    _parameters(p, {"threshold": "number", "window_s": "number", "min_duration_s": "number"})
    if "threshold" not in p or p["threshold"] <= 0 or p.get("window_s", .05) <= 0 or p.get("min_duration_s", .05) <= 0:
        raise ValueError("Explicit positive amplitude threshold and positive timing parameters required")


def _wavelet_validate(p):
    _parameters({k: v for k, v in p.items() if k != "frequencies_hz"}, {"wavelet": "text"})
    if len(p.get("wavelet", "morl")) > 64:
        raise ValueError("Wavelet name must be bounded")
    frequencies = p.get("frequencies_hz")
    if frequencies is not None and (not isinstance(frequencies, list) or not 1 <= len(frequencies) <= 64
            or any(isinstance(f, bool) or not isinstance(f, (int, float)) or not math.isfinite(f) or f <= 0 for f in frequencies)
            or any(a >= b for a, b in zip(frequencies, frequencies[1:]))):
        raise ValueError("Provide 1..64 positive increasing finite wavelet frequencies")


def _wavelet(i, p, c):
    signal = i["signal"]
    frequencies = p.get("frequencies_hz", np.geomspace(1, min(signal.sfreq / 3, 40), 16))
    _json_budget(c, 2 * len(frequencies) * signal.data.size)
    actual, coefficients = engine.wavelet_transform(signal, wavelet=p.get("wavelet", "morl"), frequencies=frequencies)
    return {"out": {**_base(signal), "representation": "continuous wavelet coefficients, not calibrated PSD",
                    "shape_order": ["frequency", "channel", "sample"], "frequencies_hz": actual.tolist(),
                    "times_s": (np.arange(signal.data.shape[1]) / signal.sfreq).tolist(),
                    "real": coefficients.real.tolist(), "imaginary": coefficients.imag.tolist(),
                    "input_amplitude_unit": signal.unit, "wavelet": p.get("wavelet", "morl"),
                    "scope": "Coefficient normalization depends on wavelet/scale; edge effects remain."}}


def register_scientific_nodes(registry):
    signal = Port("signal")
    definitions = [
        Definition("fft", {"signal": signal}, {"out": Port("json")}, _fft, _empty,
                   description="Actual one-sided FFT amplitudes, input amplitude units; rectangular window"),
        Definition("stft", {"signal": signal}, {"out": Port("json")},
                   lambda i, p, c: _time_frequency(i, p, c, density=False), _psd_validate,
                   description="Complex STFT coefficients; real/imaginary components, no boundary extension"),
        Definition("spectrogram", {"signal": signal}, {"out": Port("json")},
                   lambda i, p, c: _time_frequency(i, p, c, density=True), _psd_validate,
                   description="Actual time-frequency PSD density, physical squared units/Hz"),
        Definition("multitaper", {"signal": signal}, {"out": Port("spectrum")}, _multitaper, _multitaper_validate,
                   description="Equal-weight DPSS spectral density; explicit taper allocation bounds"),
        Definition("spectral_entropy", {"spectrum": Port("spectrum")}, {"out": Port("json")}, _entropy, _entropy_validate,
                   description="Discrete spectral-bin entropy, normalized or in bits"),
        Definition("band_power", {"spectrum": Port("spectrum")}, {"out": Port("json")}, _band, _band_validate,
                   description="Band integration only within fully measured frequency support"),
        Definition("bipolar", {"signal": signal}, {"out": signal}, _bipolar, _bipolar_validate,
                   description="Explicit bipolar channel pairs with preserved reference/history"),
        Definition("plv", {"signal": signal}, {"out": Port("json")}, _plv, _empty,
                   description="Hilbert-phase PLV; caller must band-limit/exclude edges; no neural-source claim"),
        Definition("bad_channels", {"signal": signal}, {"out": Port("json")},
                   lambda i, p, c: {"out": {"candidates": engine.bad_channel_candidates(i["signal"], **p),
                                             "scope": "Heuristic candidates only; not artifact ground truth"}}, _bad_validate,
                   description="Flatline/high-variance channel review candidates"),
        Definition("epochs", {"signal": signal}, {"out": Port("epochs")}, _epochs, _epochs_validate,
                   description="Event-centered epochs with explicit baseline; no events silently dropped"),
        Definition("epoch_average", {"epochs": Port("epochs")}, {"out": signal},
                   lambda i, p, c: {"out": i["epochs"].average()}, _empty,
                   description="Actual event average retaining units/reference/event provenance"),
        Definition("epoch_info", {"epochs": Port("epochs")}, {"out": Port("json")}, _epoch_info, _empty,
                   description="Inspect event samples, epoch support, baseline/reference metadata"),
        Definition("emg_features", {"signal": Port("signal", modality="emg")}, {"out": Port("json")},
                   lambda i, p, c: {"out": engine.emg_features(i["signal"], **p)}, _emg_validate,
                   description="RMS/MAV/waveform length/crossings/frequency descriptors in explicit input units"),
        Definition("emg_activation", {"signal": Port("signal", modality="emg")}, {"out": Port("json")},
                   lambda i, p, c: {"out": engine.activation_intervals(i["signal"], **p)}, _activation_validate,
                   description="Trailing RMS threshold candidates, not verified physiological onset"),
    ]
    if find_spec("mne") is not None and find_spec("sklearn") is not None:
        definitions.append(Definition("ica", {"signal": signal}, {"out": signal}, _ica, _ica_validate,
                                      description="MNE FastICA only with explicit reviewed component list; convergence failures stop execution"))
    if find_spec("pywt") is not None:
        definitions.append(Definition("wavelet", {"signal": signal}, {"out": Port("json")}, _wavelet, _wavelet_validate,
                                      description="PyWavelets CWT real/imaginary coefficients; explicitly not calibrated PSD"))
    for definition in definitions:
        definition = replace(definition, parallel_safe=definition.kind != "ica")
        registry.register(definition, trusted=True)
