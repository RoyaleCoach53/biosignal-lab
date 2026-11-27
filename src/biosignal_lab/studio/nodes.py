"""Reviewed built-in nodes. Optional engine nodes are registered only when installed."""
from __future__ import annotations

from dataclasses import replace
import csv
import numbers

import numpy as np

from ..analysis import compute_psd, band_powers
from ..io import read_csv
from ..models import Recording
from ..pipeline import analyze, default_config
from ..report import html_report
from ..simulate import synthetic_recording
from .runtime import Definition, Registry, Port, WorkflowError


def _parameters(parameters, fields):
    if set(parameters) - set(fields):
        raise ValueError(f"Unknown parameters: {sorted(set(parameters) - set(fields))}")
    for key, value in parameters.items():
        kind = fields[key]
        if kind == "number" and (isinstance(value, bool) or not isinstance(value, numbers.Real) or not np.isfinite(value)):
            raise ValueError(f"{key} must be a finite number")
        if kind == "integer" and type(value) is not int:
            raise ValueError(f"{key} must be an integer")
        if kind == "text" and not isinstance(value, str):
            raise ValueError(f"{key} must be text")
        if kind == "boolean" and type(value) is not bool:
            raise ValueError(f"{key} must be boolean")
        if isinstance(kind, tuple) and value not in kind:
            raise ValueError(f"{key} must be one of {kind}")


def _empty(parameters):
    _parameters(parameters, {})


def _simulate_validate(p):
    _parameters(p, {"duration_s": "number", "sfreq": "number", "n_channels": "integer",
                    "modality": ("eeg", "emg"), "seed": "integer", "with_artifacts": "boolean"})
    if not 1 <= p.get("duration_s", 10) <= 3600 or not 40 <= p.get("sfreq", 250) <= 4000:
        raise ValueError("Simulation requires duration 1..3600 seconds and sampling rate 40..4000 Hz")
    if not 1 <= p.get("n_channels", 2) <= 128 or p.get("seed", 42) < 0:
        raise ValueError("Simulation requires 1..128 channels and a nonnegative seed")


def _simulate(inputs, p, context):
    values = p.get("duration_s", 10) * p.get("sfreq", 250) * p.get("n_channels", 2)
    if values > context.limits.max_signal_values:
        raise WorkflowError("Simulation exceeds configured sample-value limit before allocation")
    return {"out": synthetic_recording(**({"duration_s": 10, "n_channels": 2} | p))}


def _csv_validate(p):
    _parameters(p, {"path": "text", "sfreq": "number", "unit": ("uv", "mv", "v"),
                    "modality": ("eeg", "emg"), "time_column": "text"})
    if "path" not in p or "sfreq" not in p or p["sfreq"] <= 0:
        raise ValueError("CSV source requires path and positive sfreq")


def _csv(inputs, p, context):
    path = context.resolve_source(p["path"])
    # Bound row/column counts without constructing a complete pandas matrix.
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = csv.reader(handle)
        header = next(rows, [])
        if not 1 <= len(header) <= 1024:
            raise WorkflowError("Studio CSV requires 1..1024 columns")
        channels = len(header) - int(p.get("time_column") in header)
        count = 0
        for row in rows:
            if not row:
                continue
            count += 1
            if count * max(1, channels) > context.limits.max_signal_values:
                raise WorkflowError("CSV exceeds configured sample-value limit before matrix allocation")
    kwargs = {k: v for k, v in p.items() if k != "path"}
    return {"out": read_csv(path, **kwargs)}


def _analyze_validate(p):
    fields = {"highpass_hz", "lowpass_hz", "notch_hz", "notch_quality", "window_s",
              "artifact_window_s", "artifact_threshold_mad", "flatline_tolerance_uv",
              "max_missing_fraction", "max_gap_s"}
    _parameters({k: v for k, v in p.items() if v is not None}, dict.fromkeys(fields, "number"))
    if set(p) - fields or any(v is None and k not in {"highpass_hz", "lowpass_hz", "notch_hz"} for k, v in p.items()):
        raise ValueError("Invalid analysis parameter")


def _analyze(inputs, p, context):
    recording = inputs["signal"]
    config = replace(default_config(recording.modality, recording.sfreq), **p)
    return {"out": analyze(recording, config)}


def _psd_validate(p):
    _parameters(p, {"window_s": "number"})
    if p.get("window_s", 2) <= 0:
        raise ValueError("window_s must be positive")


def _psd(inputs, p, context):
    recording = inputs["signal"]
    window = p.get("window_s", 2)
    if window > recording.duration_s or not np.all(np.isfinite(recording.data_uv)):
        raise ValueError("PSD requires finite samples and a window within the recording")
    frequencies, power = compute_psd(recording.data_uv, recording.sfreq, window)
    return {"out": {"frequencies": frequencies, "power": power, "sfreq": recording.sfreq,
                    "unit": "uV^2/Hz", "channels": recording.channels, "modality": recording.modality}}


def _combine(inputs, p, context):
    left, right = inputs["left"], inputs["right"]
    if left.sfreq != right.sfreq or left.data_uv.shape[1] != right.data_uv.shape[1]:
        raise WorkflowError("Channel combination requires identical sampling rates and sample counts")
    if left.modality != right.modality:
        raise WorkflowError("Channel combination requires identical modalities")
    names = left.channels + right.channels
    if len(set(names)) != len(names):
        raise WorkflowError("Channel combination requires distinct channel names")
    if left.data_uv.size + right.data_uv.size > context.limits.max_signal_values:
        raise WorkflowError("Combined signal exceeds sample-value limit")
    return {"out": Recording(np.concatenate([left.data_uv, right.data_uv]), left.sfreq,
                             names, left.modality, "studio_combination")}


def builtin_registry(*, include_engine: bool = True) -> Registry:
    registry = Registry()
    signal = Port("recording", unit="uV")
    definitions = [
        Definition("simulate", {}, {"out": signal}, _simulate, _simulate_validate,
                   description="Seeded synthetic EEG/EMG; no human recording"),
        Definition("csv", {}, {"out": signal}, _csv, _csv_validate, pure=False,
                   description="Read CSV from explicitly allowed local source directory"),
        Definition("analyze", {"signal": signal}, {"out": Port("analysis")}, _analyze,
                   _analyze_validate, description="Validated offline EEG/EMG processing and quality metrics"),
        Definition("processed", {"analysis": Port("analysis")}, {"out": signal},
                   lambda i, p, c: {"out": Recording(i["analysis"].processed_uv.copy(), i["analysis"].recording.sfreq,
                                                    i["analysis"].recording.channels, i["analysis"].recording.modality,
                                                    "studio_processed")}, _empty,
                   description="Extract processed recording from analysis"),
        Definition("summary", {"analysis": Port("analysis")}, {"out": Port("json")},
                   lambda i, p, c: {"out": i["analysis"].summary()}, _empty,
                   description="Machine-readable analysis summary"),
        Definition("html", {"analysis": Port("analysis")}, {"out": Port("html")},
                   lambda i, p, c: {"out": html_report(i["analysis"])}, _empty, pure=False,
                   description="Escaped self-contained HTML report, timestamped at execution"),
        Definition("psd", {"signal": signal}, {"out": Port("spectrum")}, _psd, _psd_validate,
                   description="Welch PSD from finite recording samples"),
        Definition("bands", {"spectrum": Port("spectrum", unit="uV^2/Hz", modality="eeg")},
                   {"out": Port("json")},
                   lambda i, p, c: {"out": band_powers(i["spectrum"]["frequencies"], i["spectrum"]["power"],
                                                      i["spectrum"]["channels"])}, _empty,
                   description="EEG band integration with unsupported bands unavailable"),
        Definition("combine", {"left": signal, "right": signal}, {"out": signal},
                   _combine, _empty, description="Concatenate channels after sampling/unit/modality checks"),
    ]
    for definition in definitions:
        registry.register(definition, trusted=True)
    if include_engine:
        try:
            from .engine_nodes import register_engine_nodes
            register_engine_nodes(registry)
        except ImportError:
            pass
    return registry
