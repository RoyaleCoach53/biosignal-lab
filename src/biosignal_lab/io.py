"""Deterministic CSV and optional EDF import, explicit signal units."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from .models import Recording

UNIT_SCALE_UV = {"uv": 1.0, "µv": 1.0, "mv": 1_000.0, "v": 1_000_000.0}


def read_csv(path: str | Path, *, sfreq: float, modality: str = "eeg",
             unit: str = "uv", time_column: str | None = None,
             channels: list[str] | None = None) -> Recording:
    """CSV: one signal channel per column; optional time column is ignored after validation.

    Caller MUST specify sampling frequency in hertz. Values are converted to microvolts.
    """
    path = Path(path)
    frame = pd.read_csv(path)
    if frame.empty:
        raise ValueError("CSV is empty")
    if time_column:
        if time_column not in frame:
            raise ValueError(f"Missing time column: {time_column}")
        times = pd.to_numeric(frame[time_column], errors="raise").to_numpy(dtype=float)
        if not np.all(np.isfinite(times)) or np.any(np.diff(times) <= 0):
            raise ValueError("Time column must be finite and strictly increasing")
        # Uniformly-sampled signal processing is invalid if the declared sample
        # rate contradicts the actual time base. Explicitly reject, do not guess.
        if not np.isfinite(sfreq) or sfreq <= 0:
            raise ValueError("Sampling frequency must be finite and positive")
        diffs = np.diff(times)
        target = 1.0 / sfreq
        if not np.isclose(np.median(diffs), target, rtol=.02, atol=1e-10):
            raise ValueError("CSV sampling frequency disagrees with timestamp spacing (seconds)")
        if np.max(np.abs(diffs - target)) > max(.05 * target, 1e-10):
            raise ValueError("Irregular CSV timestamp spacing: resample with a documented method first")
        frame = frame.drop(columns=[time_column])
    if channels:
        missing = set(channels).difference(frame.columns)
        if missing:
            raise ValueError(f"Unknown channel names: {sorted(missing)}")
        frame = frame.loc[:, channels]
    if frame.shape[1] == 0:
        raise ValueError("CSV has no signal columns")
    key = unit.strip().lower()
    if key not in UNIT_SCALE_UV:
        raise ValueError("Unit must be uv, mv or v")
    matrix = frame.apply(pd.to_numeric, errors="raise").to_numpy(dtype=np.float64).T
    return Recording(matrix * UNIT_SCALE_UV[key], sfreq, tuple(map(str, frame.columns)),
                     modality=modality, source=path.name)


def read_edf(path: str | Path, *, modality: str = "eeg", max_duration_s: float | None = 600.0) -> Recording:
    """Read EDF with MNE; MNE outputs volts for EEG/EMG. Limit data duration by default.

    Annotations and mixed sampling frequencies require specialist review; the tool does not
    automatically interpret annotation labels as clinical events.
    """
    try:
        import mne
    except ImportError as exc:
        raise RuntimeError("EDF support requires: pip install '.[edf]'") from exc
    if modality not in ("eeg", "emg"):
        raise ValueError("modality must be eeg or emg")
    # infer_types=True allows e.g. 'EMG Chin' labels to be typed as EMG.
    # Never silently combine channels from incompatible biological modalities.
    raw = mne.io.read_raw_edf(str(path), preload=False, infer_types=True, verbose="ERROR")
    raw.pick(picks=modality)
    if len(raw.ch_names) == 0:
        raise ValueError(f"No correctly labeled {modality.upper()} channels found in EDF; verify EDF channel types")
    if max_duration_s is not None and raw.times[-1] > max_duration_s:
        raw.crop(tmax=max_duration_s, include_tmax=False)
    data_v = raw.get_data()
    return Recording(data_v * 1e6, float(raw.info["sfreq"]), tuple(raw.ch_names),
                     modality=modality, source=Path(path).name)
