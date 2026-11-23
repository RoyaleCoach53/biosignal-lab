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


def test_pilot_rejects_corrupt_cached_record_before_edf_import(tmp_path, monkeypatch):
    from tools import physionet_pilot
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "S001R01.edf").write_bytes(b"corrupt")
    monkeypatch.setattr(physionet_pilot, "read_edf", lambda *a, **k: pytest.fail("Corrupt cache reached EDF reader"))
    destination = tmp_path / "out.json"
    assert main(["--subjects", "1", "--runs", "1", "--data-dir", str(cache), "--output", str(destination)]) == 1
    report = json.loads(destination.read_text())
    assert "ValueError" in report["records"][0]["error"]
    assert str(tmp_path) not in destination.read_text()


@pytest.mark.parametrize("arguments", [["--subjects", "4"], ["--subjects", "1", "1"], ["--runs", "1", "1"]])
def test_pilot_rejects_unpinned_or_duplicate_selection(arguments):
    with pytest.raises(SystemExit):
        main(arguments)


def test_negative_psd_cannot_pass_even_inside_absolute_tolerance():
    recording = Recording(np.zeros((1, 1600)), 160, ("EEG",))
    result = analyze(recording, AnalysisConfig(highpass_hz=None, lowpass_hz=None, notch_hz=None))
    result.psd_uv2_per_hz[0, 0] = -1e-12
    assert not compare_psd(result)["passed"]
