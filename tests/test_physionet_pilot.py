"""Offline tests for the opt-in public EEG interoperability pilot."""
import json

import numpy as np
import pytest

pytest.importorskip("mne")
from biosignal_lab.models import AnalysisConfig, Recording
from biosignal_lab.pipeline import analyze
from tools.physionet_pilot import compare_psd, main


def test_human_pilot_reference_psd_matches_on_synthetic_controls():
    rng = np.random.default_rng(20261122)
    fs = 160.0
    samples = 3200
    time_s = np.arange(samples) / fs
    data = np.stack([
        12 * np.sin(2 * np.pi * 10 * time_s) + rng.normal(0, 1, samples),
        8 * np.sin(2 * np.pi * 20 * time_s) + rng.normal(0, 2, samples),
    ])
    recording = Recording(data, fs, ("EEG1", "EEG2"))
    config = AnalysisConfig(
        highpass_hz=None, lowpass_hz=None, notch_hz=None, window_s=4.0
    )
    result = analyze(recording, config)
    verification = compare_psd(result)
    assert verification["passed"]
    assert verification["failing_bins"] == 0
    assert verification["bins_compared"] > 100

    # Regression control: a corrupted value must be rejected, not reported as pass.
    result.psd_uv2_per_hz[0, 15] += 1e6
    assert not compare_psd(result)["passed"]


def test_human_pilot_fails_closed_offline_when_edf_missing(tmp_path, monkeypatch):
    import mne

    def forbidden(*args, **kwargs):
        raise AssertionError("Runner attempted a download without --download")

    monkeypatch.setattr(mne.datasets.eegbci, "load_data", forbidden)
    destination = tmp_path / "result.json"
    exit_code = main([
        "--subjects", "1", "--runs", "1",
        "--data-dir", str(tmp_path / "empty"),
        "--output", str(destination),
    ])
    assert exit_code == 1
    report = json.loads(destination.read_text(encoding="utf-8"))
    assert not report["passed"]
    assert report["records"][0]["subject"] == 1
    assert "FileNotFoundError" in report["records"][0]["error"]
