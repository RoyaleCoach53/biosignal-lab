"""Release-review regressions added after reproducing the original 73 tests."""
from pathlib import Path

import numpy as np
import pytest

from biosignal_lab.analysis import pairwise_coherence
from biosignal_lab.models import Recording
from biosignal_lab.pipeline import analyze
from biosignal_lab.simulate import synthetic_recording


@pytest.mark.parametrize("seconds", [10, 30, 60])
def test_dashboard_renders_complete_demo(seconds):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    app = Path(__file__).resolve().parents[1] / "app.py"
    dashboard = AppTest.from_file(str(app), default_timeout=60).run()
    if seconds != 30:
        duration = next(x for x in dashboard.slider if x.label == "Duration (seconds)")
        duration.set_value(seconds).run()
    assert not dashboard.exception
    assert len(dashboard.metric) >= 4
    assert any(x.label == "Channels" for x in dashboard.metric)


def test_dashboard_emg_demo_renders():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    app = Path(__file__).resolve().parents[1] / "app.py"
    dashboard = AppTest.from_file(str(app), default_timeout=60).run()
    next(x for x in dashboard.selectbox if x.label == "Signal type").set_value("emg").run()
    assert not dashboard.exception
    assert len(dashboard.metric) >= 4


def test_half_second_recording_does_not_create_equal_bound_sliders(monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    import biosignal_lab.simulate

    t = np.arange(125) / 250
    recording = Recording(np.vstack([np.sin(2 * np.pi * 10 * t),
                                    np.sin(2 * np.pi * 15 * t)]), 250, ("A", "B"))
    monkeypatch.setattr(biosignal_lab.simulate, "synthetic_recording", lambda **kwargs: recording)
    app = Path(__file__).resolve().parents[1] / "app.py"
    dashboard = AppTest.from_file(str(app), default_timeout=60).run()
    assert not dashboard.exception
    assert any("Coherence unavailable" in message.value for message in dashboard.info)


def test_single_segment_coherence_rejected():
    rng = np.random.default_rng(7)
    with pytest.raises(ValueError, match="two.*segments"):
        pairwise_coherence(rng.normal(size=500), rng.normal(size=500), 250, window_s=2)


@pytest.mark.parametrize("constant", [0.0, 10.0])
def test_constant_channel_coherence_rejected(constant):
    with pytest.raises(ValueError, match="constant"):
        pairwise_coherence(np.full(2000, constant), np.arange(2000), 250)


def test_fractional_sample_gap_limit_is_not_rounded_up():
    fs = 15
    data = np.sin(2 * np.pi * 2 * np.arange(300) / fs)[None]
    data[0, 100:102] = np.nan  # 0.133 s, exceeds the default 0.1 s limit
    with pytest.raises(ValueError, match="maximum interpolation duration"):
        analyze(Recording(data, fs, ("EEG",)))


def test_fractional_sample_gap_within_limit_still_interpolates():
    fs = 15
    data = np.sin(2 * np.pi * 2 * np.arange(300) / fs)[None]
    data[0, 100] = np.nan  # 0.067 s, within the limit
    result = analyze(Recording(data, fs, ("EEG",)))
    assert any("interpolated" in warning for warning in result.warnings)


@pytest.mark.parametrize("fs", [40, 100])
def test_simulator_omits_tones_at_or_above_nyquist(monkeypatch, fs):
    class NoNoise:
        def normal(self, loc=0, scale=1, size=None):
            return np.zeros(size)

    monkeypatch.setattr(np.random, "default_rng", lambda seed: NoNoise())
    rec = synthetic_recording(sfreq=fs, duration_s=2, n_channels=1, with_artifacts=False)
    t = np.arange(2 * fs) / fs
    expected = 22 * np.sin(2 * np.pi * 10 * t) + 10 * np.sin(2 * np.pi * 6 * t)
    if fs / 2 > 20:
        expected += 4 * np.sin(2 * np.pi * 20 * t)
    np.testing.assert_allclose(rec.data_uv[0], expected, atol=1e-10)
