"""Explicit signal units and immutable, provenance-preserving transformations."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Mapping
import copy
import numpy as np

ELECTRICAL_UNITS = {"V": 1.0, "mV": 1e-3, "uV": 1e-6}
MODALITIES = {"eeg", "emg", "ecg", "eog", "ppg", "eda", "other"}


@dataclass(frozen=True)
class Signal:
    """Channels x samples; units are explicit and never inferred from modality.

    PPG may use arbitrary units (``a.u.``); EDA may use Siemens (``S``) or
    microsiemens (``uS``). No electrical conversion is applied to either.
    Missing values must be handled explicitly before creating a Signal.
    """

    data: np.ndarray
    sfreq: float
    channels: tuple[str, ...]
    modality: str = "eeg"
    unit: str = "uV"
    reference: str | None = None
    metadata: Mapping = field(default_factory=dict)
    history: tuple[dict, ...] = ()

    def __post_init__(self):
        if np.iscomplexobj(self.data):
            raise ValueError("Signal amplitudes must be real, not complex coefficients")
        data = np.array(self.data, dtype=np.float64, copy=True)
        if data.ndim != 2 or min(data.shape) < 1 or not np.all(np.isfinite(data)):
            raise ValueError("Signal requires finite channels x samples")
        if not np.isfinite(self.sfreq) or self.sfreq <= 0:
            raise ValueError("sfreq must be finite and positive")
        channels = tuple(self.channels)
        if (
            len(channels) != data.shape[0]
            or len(set(channels)) != len(channels)
            or any(not isinstance(c, str) or not c for c in channels)
        ):
            raise ValueError("Unique nonempty channel labels must match data")
        if self.modality not in MODALITIES or self.unit not in {
            *ELECTRICAL_UNITS,
            "S",
            "uS",
            "a.u.",
        }:
            raise ValueError("Unsupported modality or unit")
        if self.reference is not None and not isinstance(self.reference, str):
            raise ValueError("reference must be text or None")
        data.setflags(write=False)
        object.__setattr__(self, "data", data)
        object.__setattr__(self, "channels", channels)
        object.__setattr__(self, "metadata", MappingProxyType(copy.deepcopy(dict(self.metadata))))
        object.__setattr__(self, "history", tuple(copy.deepcopy(self.history)))

    @property
    def duration_s(self):
        return self.data.shape[1] / self.sfreq

    def transformed(self, data, operation: str, *, parameters=None, **changes):
        return replace(
            self,
            data=data,
            history=(*self.history, {"operation": operation, "parameters": parameters or {}}),
            **changes,
        )

    def to_unit(self, unit: str):
        scales = ELECTRICAL_UNITS if self.unit in ELECTRICAL_UNITS else {"S": 1.0, "uS": 1e-6}
        if self.unit == unit:
            return self.transformed(
                self.data, "unit_conversion", parameters={"from": self.unit, "to": unit}
            )
        if self.unit not in scales or unit not in scales:
            raise ValueError("Incompatible units; arbitrary units cannot be converted")
        return self.transformed(
            self.data * scales[self.unit] / scales[unit],
            "unit_conversion",
            parameters={"from": self.unit, "to": unit},
            unit=unit,
        )

    @classmethod
    def from_recording(cls, recording):
        return cls(
            recording.data_uv,
            recording.sfreq,
            recording.channels,
            recording.modality,
            "uV",
            metadata={"source": recording.source},
        )
