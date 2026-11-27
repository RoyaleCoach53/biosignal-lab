"""Reference checks for channel handling and descriptive spectral coupling."""

import numpy as np
import pytest
from scipy.signal import coherence
from biosignal_lab.engine import Signal, band_features, coherence_matrix, handle_bad_channels


def test_band_features_preserve_units_and_unavailable_ranges():
    time = np.arange(2000) / 100
    signal = Signal((10 * np.sin(2 * np.pi * 10 * time))[None], 100, ("alpha",))
    result = band_features(signal)[0]
    assert result["power_unit"] == "uV^2"
    assert result["bands"]["alpha"]["absolute"] == pytest.approx(50, rel=0.001)
    assert result["bands"]["alpha"]["relative"] == pytest.approx(1, abs=0.001)
    low = Signal(signal.data[:, ::4], 25, signal.channels)
    result = band_features(low)[0]
    assert result["bands"]["gamma"]["absolute"] is None and result["reference_power"] is None
    assert result["bands"]["gamma"]["coverage"] == 0
    zero = band_features(Signal(np.zeros((1, 1000)), 100, ("zero",)))[0]
    assert zero["bands"]["alpha"]["absolute"] == 0 and zero["bands"]["alpha"]["relative"] is None


def test_coherence_matches_scipy_symmetric_bounded_and_rejects_degenerate():
    rng = np.random.default_rng(42)
    x = rng.normal(size=2000)
    signal = Signal(np.array([x, x + 0.2 * rng.normal(size=2000)]), 100, ("a", "b"))
    frequencies, coupling = coherence_matrix(signal, window_s=2)
    expected_f, expected = coherence(
        signal.data[0],
        signal.data[1],
        fs=100,
        window="hann",
        nperseg=200,
        noverlap=100,
        detrend="constant",
    )
    np.testing.assert_allclose(frequencies, expected_f)
    np.testing.assert_allclose(coupling[:, 0, 1], expected)
    np.testing.assert_array_equal(coupling[:, 0, 1], coupling[:, 1, 0])
    assert np.all((coupling >= 0) & (coupling <= 1))
    with pytest.raises(ValueError, match="2 Welch"):
        coherence_matrix(Signal(signal.data[:, :200], 100, ("a", "b")), window_s=2)


def test_reviewed_bad_channel_drop_and_spline_interpolation():
    pytest.importorskip("mne")
    channels = ("Fp1", "Fp2", "F3", "F4", "C3", "C4", "O1", "O2")
    data = np.ones((8, 500))
    data[4] = 99.0
    signal = Signal(data, 100, channels, reference="synthetic_zero")
    dropped = handle_bad_channels(signal, ["C3"])
    assert dropped.channels == tuple(c for c in channels if c != "C3")
    assert dropped.reference == signal.reference
    interpolated = handle_bad_channels(signal, ["C3"], method="interpolate")
    np.testing.assert_allclose(interpolated.data[4], 1, atol=1e-6)
    np.testing.assert_array_equal(
        interpolated.data[np.arange(8) != 4], signal.data[np.arange(8) != 4]
    )
    assert interpolated.history[-1]["parameters"]["interpolated"] == ["C3"]
    with pytest.raises(ValueError):
        handle_bad_channels(signal, ["unknown"])
    with pytest.raises(ValueError, match="every"):
        handle_bad_channels(signal, channels)
