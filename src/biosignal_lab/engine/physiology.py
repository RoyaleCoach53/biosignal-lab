"""Optional established peripheral-processing pipelines with explicit limitations."""

from __future__ import annotations
from dataclasses import dataclass
import hashlib
import warnings
import numpy as np
from .model import Signal


def _json_value(value):
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_json_value(v) for v in value]
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"Unsupported processing metadata type: {type(value).__name__}")


@dataclass
class PeripheralResult:
    """Original NeuroKit sample table/info plus complete processing provenance.

    Sample-table NaNs may represent unavailable/interpolated features; they are
    preserved, not labelled successful detections. summary() encodes them as null.
    """

    signals: object
    info: dict
    provenance: dict

    def summary(self):
        rates = {}
        for name in self.signals:
            if name.endswith("_Rate"):
                data = self.signals[name].to_numpy(dtype=float)
                valid = data[np.isfinite(data)]
                rates[name] = {
                    "median_per_min": float(np.median(valid)) if len(valid) else None,
                    "available_samples": int(len(valid)),
                    "total_samples": int(len(data)),
                }
        return _json_value(
            {
                "scope": "research descriptions requiring reviewed event identity; no diagnosis or validated physiological accuracy",
                "provenance": self.provenance,
                "info": self.info,
                "rate_descriptions": rates,
                "columns": list(self.signals.columns),
            }
        )


def process_peripheral(signal: Signal, *, channel: str, method=None):
    """Run an explicit NeuroKit2 ECG, PPG, EDA or positive-polarity EOG workflow.

    Electrical signals are converted to mV, EDA to uS, PPG must be arbitrary
    units. Only one explicitly selected channel is processed. No network calls,
    automatic diagnosis, medical labels, or unverifiable accuracy claims occur.
    """
    import neurokit2 as nk

    defaults = {
        "ecg": "neurokit",
        "ppg": "elgendi",
        "eda": "neurokit",
        "eog": "neurokit-clean+mne-peaks",
    }
    minima = {"ecg": 100, "ppg": 25, "eda": 10, "eog": 50}
    if signal.modality not in defaults or channel not in signal.channels:
        raise ValueError("Select a known channel from ECG/PPG/EDA/EOG Signal")
    if not float(signal.sfreq).is_integer() or signal.sfreq < minima[signal.modality]:
        raise ValueError(
            "This workflow requires an integer sample rate above its documented modality minimum"
        )
    if signal.duration_s < 10 or signal.data.shape[1] > 1_000_000:
        raise ValueError("Peripheral workflow requires 10 seconds through 1,000,000 samples")
    if method is None:
        method = defaults[signal.modality]
    allowed = {
        "ecg": {"neurokit", "pantompkins1985", "hamilton2002"},
        "ppg": {"elgendi"},
        "eda": {"neurokit"},
        "eog": {"neurokit-clean+mne-peaks"},
    }
    if method not in allowed[signal.modality]:
        raise ValueError("Unsupported explicit processing method")
    target = (
        "mV" if signal.modality in {"ecg", "eog"} else "uS" if signal.modality == "eda" else "a.u."
    )
    converted = signal.to_unit(target)
    index = signal.channels.index(channel)
    values = converted.data[index]
    if np.ptp(values) <= 0:
        raise ValueError("Constant signal cannot support meaningful peripheral event detection")
    processors = {
        "ecg": nk.ecg_process,
        "ppg": nk.ppg_process,
        "eda": nk.eda_process,
        "eog": nk.eog_process,
    }
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        if signal.modality == "eog":
            import pandas as pd

            cleaned = nk.eog_clean(
                values.copy(), sampling_rate=int(signal.sfreq), method="neurokit"
            )
            markers, info = nk.eog_peaks(cleaned, sampling_rate=int(signal.sfreq), method="mne")
            rate = nk.signal_rate(
                info["EOG_Blinks"], sampling_rate=int(signal.sfreq), desired_length=len(values)
            )
            table = pd.DataFrame(
                {
                    "EOG_Raw": values,
                    "EOG_Clean": cleaned,
                    "EOG_Blinks": markers["EOG_Blinks"],
                    "EOG_Rate": rate,
                }
            )
        else:
            table, info = processors[signal.modality](
                values.copy(), sampling_rate=int(signal.sfreq), method=method
            )
    if len(table) != signal.data.shape[1]:
        raise ValueError("Peripheral library changed sample count unexpectedly")
    if np.any(np.isinf(table.select_dtypes(include=["number"]).to_numpy())):
        raise ValueError("Peripheral pipeline produced infinite output; inspect input scaling")
    provenance = {
        "library": "NeuroKit2",
        "version": nk.__version__,
        "modality": signal.modality,
        "method": method,
        "channel": channel,
        "sfreq_hz": signal.sfreq,
        "input_unit": signal.unit,
        "processing_unit": target,
        "reference": signal.reference,
        "input_data_sha256": hashlib.sha256(signal.data[index].tobytes()).hexdigest(),
        "input_metadata": dict(signal.metadata),
        "input_history": signal.history,
        "processing_direction": "offline; library filters/rates may be acausal; no real-time claim",
        "warnings": [
            {"category": type(item.message).__name__, "message": str(item.message)[:500]}
            for item in observed
        ],
        "limitations": "Synthetic engineering verification only; review detections. No clinical accuracy, diagnostic suitability, physiological ground truth or independent validation established.",
    }
    return PeripheralResult(table, info, provenance)
