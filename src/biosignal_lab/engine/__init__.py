"""Research engine primitives with explicit units, provenance and failure modes.

This additive API leaves the verified v0.3 Recording/analyze workflow intact.
No feature in this package makes a clinical or hardware compatibility claim.
"""

from .model import Signal
from .filters import (
    FilterSpec,
    StreamingFilter,
    filter_signal,
    resample_signal,
    detrend_signal,
    normalize_signal,
    repair_missing,
)
from .spectral import (
    welch_psd,
    fft_spectrum,
    stft,
    spectrogram,
    multitaper_psd,
    spectral_entropy,
    integrate_band,
    wavelet_transform,
    discrete_wavelet,
)
from .eeg import (
    Epochs,
    common_average_reference,
    bipolar_reference,
    epoch,
    phase_locking_value,
    bad_channel_candidates,
    ica_remove,
)
from .features import (
    emg_features,
    activation_intervals,
    peak_intervals,
    eda_components,
    adaptive_cancel,
)
from .io import save_signal, load_signal, load_mat, load_mne, save_hdf5, load_hdf5

from .physiology import PeripheralResult, process_peripheral
from .interchange import load_bids, load_xdf
from .visualization import scalp_positions, plot_topomap, plot_montage, plot_evoked

__all__ = [
    "PeripheralResult",
    "process_peripheral",
    "load_bids",
    "load_xdf",
    "scalp_positions",
    "plot_topomap",
    "plot_montage",
    "plot_evoked",
    "repair_missing",
    "ica_remove",
    "save_hdf5",
    "load_hdf5",
    "Signal",
    "FilterSpec",
    "StreamingFilter",
    "filter_signal",
    "resample_signal",
    "detrend_signal",
    "normalize_signal",
    "welch_psd",
    "fft_spectrum",
    "stft",
    "spectrogram",
    "multitaper_psd",
    "spectral_entropy",
    "integrate_band",
    "wavelet_transform",
    "discrete_wavelet",
    "Epochs",
    "common_average_reference",
    "bipolar_reference",
    "epoch",
    "phase_locking_value",
    "bad_channel_candidates",
    "emg_features",
    "activation_intervals",
    "peak_intervals",
    "eda_components",
    "adaptive_cancel",
    "save_signal",
    "load_signal",
    "load_mat",
    "load_mne",
]
