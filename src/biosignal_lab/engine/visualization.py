"""Measured scalp-potential plots and event averages; no neural source inference."""

from __future__ import annotations
import numpy as np
from .model import Signal
from .eeg import Epochs


def _montage_info(signal, montage):
    import mne

    if signal.modality != "eeg":
        raise ValueError("Electrode montage requires EEG channel metadata")
    if montage is None:
        names = mne.channels.get_builtin_montages()
        montage = "colin27_1020" if "colin27_1020" in names else "standard_1020"
    if isinstance(montage, str):
        mounted = mne.channels.make_standard_montage(montage)
        name = montage
    elif isinstance(montage, mne.channels.DigMontage):
        mounted, name = montage.copy(), "caller_supplied"
    else:
        raise ValueError("Montage must be an MNE built-in name or explicit DigMontage")
    info = mne.create_info(list(signal.channels), signal.sfreq, "eeg")
    # Exact case-sensitive names; never guess missing electrode locations.
    info.set_montage(mounted, match_case=True, on_missing="raise")
    positions = np.asarray([channel["loc"][:3] for channel in info["chs"]])
    if not np.all(np.isfinite(positions)):
        raise ValueError("Every channel requires a finite electrode position")
    return info, name


def scalp_positions(signal: Signal, *, montage=None):
    """Return MNE head-coordinate electrode positions in metres.

    Standard templates are approximate; they are not subject digitization or
    intracranial locations. Unknown electrode labels fail rather than being placed.
    """
    info, name = _montage_info(signal, montage)
    return {
        "montage": name,
        "coordinate_frame": "head",
        "position_unit": "m",
        "channels": {channel["ch_name"]: channel["loc"][:3].tolist() for channel in info["chs"]},
        "interpretation": "scalp sensor positions, not inferred neural sources",
    }


def plot_topomap(signal: Signal, values, *, value_unit, montage=None, axes=None):
    """Plot caller-supplied channel scalars over scalp electrodes using MNE.

    The scalar unit is mandatory: raw amplitudes, powers and statistics must not
    be confused. Spatial interpolation fills between sensors; it is not a measured
    continuous field, source localization or evidence of activity in deep structures.
    """
    import matplotlib.pyplot as plt
    import mne

    values = np.asarray(values, dtype=float)
    if (
        values.shape != (len(signal.channels),)
        or len(values) < 4
        or not np.all(np.isfinite(values))
    ):
        raise ValueError("Topomap requires >=4 matching finite channel scalars")
    if not isinstance(value_unit, str) or not value_unit.strip():
        raise ValueError("Explicit scalar unit is required")
    info, _ = _montage_info(signal, montage)
    if axes is None:
        figure, axes = plt.subplots()
    else:
        figure = axes.figure
    image, _ = mne.viz.plot_topomap(
        values,
        info,
        names=list(signal.channels),
        axes=axes,
        show=False,
        extrapolate="local",
        contours=0,
    )
    figure.colorbar(image, ax=axes, label=value_unit)
    axes.set_title("Scalp interpolation (not neural sources)")
    return figure


def plot_montage(signal: Signal, *, montage=None, kind="3d"):
    """Plot actual selected electrode labels on an MNE template or given montage."""
    import mne

    if kind not in {"3d", "topomap"}:
        raise ValueError("Montage plot kind must be 3d or topomap")
    info, _ = _montage_info(signal, montage)
    return mne.viz.plot_montage(info.get_montage(), kind=kind, show_names=True, show=False)


def plot_evoked(epochs: Epochs, *, channels=None, confidence=0.95, axes=None):
    """Plot trial mean with optional pointwise Student-t intervals across trials.

    Intervals assume independent trials and are neither participant-level nor
    simultaneous inference. Repeated/correlated trials violate that assumption.
    No component is automatically classified as P300 or other physiological ERP.
    """
    import matplotlib.pyplot as plt
    from scipy.stats import t

    if confidence is not None and (not np.isfinite(confidence) or not 0 < confidence < 1):
        raise ValueError("Confidence must be in (0,1) or None")
    selected = tuple(epochs.channels if channels is None else channels)
    if (
        not selected
        or len(set(selected)) != len(selected)
        or any(ch not in epochs.channels for ch in selected)
    ):
        raise ValueError("Select unique known epoch channels")
    if confidence is not None and len(epochs.events) < 2:
        raise ValueError("Trial confidence interval requires >=2 trials; use confidence=None")
    if axes is None:
        figure, axes = plt.subplots()
    else:
        figure = axes.figure
    for channel in selected:
        data = epochs.data[:, epochs.channels.index(channel)]
        mean = data.mean(axis=0)
        line = axes.plot(epochs.times, mean, label=channel)[0]
        if confidence is not None:
            error = (
                data.std(axis=0, ddof=1)
                / np.sqrt(len(data))
                * t.ppf((1 + confidence) / 2, len(data) - 1)
            )
            axes.fill_between(
                epochs.times, mean - error, mean + error, color=line.get_color(), alpha=0.15
            )
    axes.axvline(0, color="gray", linestyle="--", label="Event")
    axes.set(
        xlabel="Time relative to event (s)",
        ylabel=f"Amplitude ({epochs.unit})",
        title=f"Event average ({len(epochs.events)} trials)",
    )
    axes.legend()
    return figure
