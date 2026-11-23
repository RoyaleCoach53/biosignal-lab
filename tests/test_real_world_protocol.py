"""Offline controls for the real-data validation harness; no human data fixtures."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("mne")
from benchmarks.real_world.validate import (DATASET_BASE, decode_uniform_edf, fetch_record,
                                           integrate_linear, reference_filter, validate_manifest)
from biosignal_lab import __version__
from biosignal_lab.models import AnalysisConfig, Recording
from biosignal_lab.pipeline import analyze
from biosignal_lab.preprocessing import preprocess


def synthetic_edf(path, unit="uV", reserved=""):
    count, samples = 1, 32
    fixed = [("0", 8), ("synthetic", 80), ("test", 80), ("01.01.24", 8),
             ("00.00.00", 8), ("512", 8), (reserved, 44), ("1", 8), ("1", 8), ("1", 4)]
    header = "".join(str(x).ljust(n) for x, n in fixed)
    for value, width in [("EEG", 16), ("", 80), (unit, 8), ("-100", 8), ("100", 8),
                         ("-32768", 8), ("32767", 8), ("", 80), (str(samples), 8), ("", 32)]:
        header += value.ljust(width) * count
    digital = np.arange(-16, 16, dtype="<i2")
    path.write_bytes(header.encode("ascii") + digital.tobytes())
    return -100 + (digital.astype(float) + 32768) * (200 / 65535)


@pytest.mark.parametrize("unit,scale", [("uV", 1), ("mV", 1000), ("V", 1e6)])
def test_independent_edf_scaling_known_digital_samples(tmp_path, unit, scale):
    path = tmp_path / "synthetic.edf"
    expected = synthetic_edf(path, unit)
    values, fs, labels = decode_uniform_edf(path)
    np.testing.assert_allclose(values[0], expected * scale)
    assert fs == 32 and labels == ("EEG",)


def test_independent_decoder_rejects_truncated_file(tmp_path):
    path = tmp_path / "truncated.edf"
    synthetic_edf(path)
    path.write_bytes(path.read_bytes()[:-2])
    with pytest.raises(ValueError, match="length mismatch"):
        decode_uniform_edf(path)


def test_independent_decoder_rejects_discontinuous_edf(tmp_path):
    path = tmp_path / "discontinuous.edf"
    synthetic_edf(path, reserved="EDF+D")
    with pytest.raises(ValueError, match="Discontinuous"):
        decode_uniform_edf(path)


def test_independent_decoder_rejects_unexpected_units(tmp_path):
    path = tmp_path / "other.edf"
    synthetic_edf(path, unit="unknown")
    with pytest.raises(ValueError, match="physical dimension"):
        decode_uniform_edf(path)


def test_band_integral_interpolates_edges_independently():
    f = np.arange(4, dtype=float)
    np.testing.assert_allclose(integrate_linear(f, np.vstack([f, 2*f]), 1.5, 2.5), [2, 4])


@pytest.mark.parametrize("config", [AnalysisConfig(),
    AnalysisConfig(highpass_hz=1, lowpass_hz=40, notch_hz=60),
    AnalysisConfig(highpass_hz=None, lowpass_hz=None, notch_hz=None)])
def test_matched_mne_filter_reference_controls(config):
    x = np.random.default_rng(33).normal(size=(2, 9600))
    ours, _ = preprocess(x, 160, config)
    reference = reference_filter(x, 160, config)
    np.testing.assert_allclose(ours, reference, rtol=1e-7, atol=1e-8)


def test_corrupt_cached_download_rejected_without_overwriting(tmp_path):
    path = tmp_path / "S001/S001R01.edf"
    path.parent.mkdir()
    path.write_bytes(b"corrupt")
    record = {"path": "S001/S001R01.edf", "url": DATASET_BASE + "S001/S001R01.edf",
              "sha256": hashlib.sha256(b"original").hexdigest()}
    with pytest.raises(ValueError, match="checksum mismatch"):
        fetch_record(record, tmp_path, False)
    assert path.read_bytes() == b"corrupt"


def test_download_rejects_unapproved_host(tmp_path):
    with pytest.raises(ValueError, match="official"):
        fetch_record({"path": "S001/S001R01.edf", "url": "https://example.com/record.edf"}, tmp_path, False)


def test_manifest_cannot_silently_duplicate_or_exclude_subjects():
    root = Path(__file__).resolve().parents[1] / "benchmarks/real_world"
    manifest, protocol = [json.loads((root / name).read_text()) for name in ["manifest.json", "protocol.json"]]
    manifest["records"][0] = manifest["records"][1]
    with pytest.raises(ValueError, match="exactly once"):
        validate_manifest(manifest, protocol)


def test_raw_and_processed_metrics_keep_notch_effect_visible():
    fs = 250
    t = np.arange(10000) / fs
    result = analyze(Recording((10*np.sin(2*np.pi*50*t) + 10*np.sin(2*np.pi*10*t))[None], fs, ("EEG",)))
    assert result.raw_channel_metrics[0]["line_50_fraction"] > .1
    assert result.channel_metrics[0]["line_50_fraction"] < .001
    summary = result.summary()
    assert summary["version"] == __version__ and summary["software"]["scipy"]
    assert summary["processing"]["notch_pad_samples"] == 9
    assert "raw_channels" in summary


def test_dashboard_shows_raw_and_processed_spectral_traces():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=60).run()
    assert not app.exception
    names = [trace.get("name") for chart in app.get("plotly_chart")
             for trace in json.loads(chart.proto.spec)["data"]]
    assert "Raw (before filters)" in names and "Processed" in names
