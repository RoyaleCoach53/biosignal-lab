"""Verify real plots and electrode coordinates using an offscreen backend."""

import numpy as np
import pytest
from biosignal_lab.engine import (
    Signal,
    epoch,
    scalp_positions,
    plot_topomap,
    plot_montage,
    plot_evoked,
)


@pytest.fixture
def eeg():
    pytest.importorskip("mne")
    return Signal(np.ones((6, 1000)), 100.0, ("Fp1", "Fp2", "C3", "C4", "O1", "O2"))


def test_montage_coordinates_are_head_frame_and_unknown_labels_fail(eeg):
    positions = scalp_positions(eeg)
    assert positions["coordinate_frame"] == "head" and positions["position_unit"] == "m"
    assert set(positions["channels"]) == set(eeg.channels)
    assert positions["channels"]["C3"][0] < 0 < positions["channels"]["C4"][0]
    assert positions["channels"]["Fp1"][1] > positions["channels"]["O1"][1]
    with pytest.raises(ValueError, match="subset"):
        scalp_positions(Signal(np.ones((1, 100)), 100, ("unknown_electrode",)))


def test_topomap_and_montage_create_real_drawable_figures(eeg, tmp_path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure = plot_topomap(eeg, np.arange(6.0), value_unit="uV")
    figure.canvas.draw()
    assert figure.axes[0].images and len(figure.axes) == 2
    path = tmp_path / "scalp.png"
    figure.savefig(path)
    assert path.stat().st_size > 1000
    montage = plot_montage(eeg, kind="topomap")
    montage.canvas.draw()
    plt.close(figure)
    plt.close(montage)
    with pytest.raises(ValueError):
        plot_topomap(eeg, np.arange(6.0), value_unit="")


def test_evoked_mean_interval_and_units_are_visible():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    time = np.arange(1000) / 100
    signal = Signal(np.sin(2 * np.pi * time)[None], 100, ("A",), unit="mV")
    epochs = epoch(signal, [200, 400, 600], -0.1, 0.4, baseline=(-0.1, 0))
    figure = plot_evoked(epochs, channels=["A"])
    figure.canvas.draw()
    trace = figure.axes[0].lines[0]
    np.testing.assert_allclose(trace.get_ydata(), epochs.data[:, 0].mean(axis=0))
    assert "mV" in figure.axes[0].get_ylabel() and len(figure.axes[0].collections) == 1
    plt.close(figure)
    one = epoch(signal, [200], -0.1, 0.4)
    with pytest.raises(ValueError, match="2 trials"):
        plot_evoked(one)
    figure = plot_evoked(one, confidence=None)
    plt.close(figure)
