"""Reproduce numerical checks; this script does not establish clinical validity."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import statistics
import sys
import time

import mne
import numpy as np
from scipy.integrate import trapezoid

from biosignal_lab.analysis import compute_psd, detect_artifacts
from biosignal_lab.io import read_csv
from biosignal_lab.models import AnalysisConfig, Recording
from biosignal_lab.pipeline import analyze
from biosignal_lab.preprocessing import preprocess
from biosignal_lab.simulate import synthetic_recording
from biosignal_lab import __version__


def sine(hz, amplitude=10.0, sfreq=250, seconds=60):
    t = np.arange(int(sfreq * seconds)) / sfreq
    return amplitude * np.sin(2 * np.pi * hz * t)


def verify() -> dict:
    checks = {}
    for hz, band in [(2, "delta"), (10, "alpha"), (35, "gamma"), (42, "gamma")]:
        result = analyze(Recording(sine(hz)[None], 250, ("EEG",)))
        measured = result.band_powers[0][f"{band}_uv2"]
        error = 100 * (measured - 50.0) / 50.0
        checks[f"eeg_{hz}hz"] = {
            "sfreq_hz": 250, "duration_s": 60, "amplitude_peak_uv": 10,
            "expected_uv2": 50.0, "measured_uv2": measured,
            "percent_error": error, "tolerance_percent": 3.0,
            "passed": abs(error) <= 3.0, "config": result.summary()["config"],
        }
    for fs in [500, 2000]:
        result = analyze(Recording(sine(200, 100, fs, 10)[None], fs, ("EMG",), "emg"))
        measured = result.channel_metrics[0]["emg_rms_uv"]
        expected = float(100 / np.sqrt(2))
        error = 100 * (measured - expected) / expected
        checks[f"emg_200hz_fs{fs}"] = {
            "sfreq_hz": fs, "duration_s": 10, "amplitude_peak_uv": 100,
            "expected_rms_uv": expected, "measured_rms_uv": measured,
            "median_frequency_hz": result.channel_metrics[0]["emg_median_frequency_hz"],
            "percent_error": error, "tolerance_percent": 2.0,
            "passed": abs(error) <= 2.0,
            "config": result.summary()["config"], "warnings": result.warnings,
        }

    rng = np.random.default_rng(909)
    x = sine(10, 12, seconds=20) + sine(35, 5, seconds=20) + rng.normal(0, 1, 5000)
    f, p = compute_psd(x[None], 250, window_s=2)
    ref, rf = mne.time_frequency.psd_array_welch(
        x * 1e-6, sfreq=250, n_fft=500, n_per_seg=500, n_overlap=250,
        window="hann", average="mean", verbose="ERROR",
    )
    checks["mne_welch_crosscheck"] = {
        "seed": 909, "nperseg": 500, "noverlap": 250, "window": "hann",
        "max_absolute_error_uv2_per_hz": float(np.max(np.abs(p[0] - ref * 1e12))),
        "passed": bool(np.array_equal(f, rf) and
                       np.allclose(p[0], ref * 1e12, rtol=1e-7, atol=1e-10)),
        "qualification": "Different library interface; shared numerical dependencies are possible.",
    }
    noise = np.random.default_rng(100).normal(0, 5, 50000)
    f, p = compute_psd(noise[None], 250)
    integrated, variance = float(trapezoid(p[0], f)), float(np.var(noise))
    checks["white_noise_power"] = {
        "seed": 100, "spectral_uv2": integrated, "variance_uv2": variance,
        "relative_tolerance": 0.08,
        "passed": abs(integrated - variance) / variance <= 0.08,
    }
    x = sine(50, 1, seconds=20) + sine(10, 1, seconds=20)
    filtered, _ = preprocess(x[None], 250, AnalysisConfig(
        highpass_hz=None, lowpass_hz=None, notch_hz=50))
    f, p = compute_psd(x[None], 250)
    _, q = compute_psd(filtered, 250)
    k = int(np.argmin(abs(f - 50)))
    ratio = float(q[0, k] / p[0, k])
    checks["notch_50hz"] = {"residual_psd_ratio": ratio, "upper_limit": 0.01,
                            "passed": ratio < 0.01}
    low_rate = analyze(Recording(sine(10, sfreq=80)[None], 80, ("EEG",)))
    checks["unsupported_gamma"] = {
        "coverage": low_rate.band_powers[0]["gamma_coverage"],
        "passed": low_rate.band_powers[0]["gamma_uv2"] is None,
    }
    damaged = sine(10, seconds=30)[None]
    damaged[0, 100:200] = np.nan
    rejected = False
    try:
        analyze(Recording(damaged, 250, ("EEG",)))
    except ValueError as exc:
        rejected = "maximum interpolation duration" in str(exc)
    checks["long_gap_rejected"] = {"gap_s": 0.4, "passed": rejected}
    disturbed = sine(10, amplitude=5, seconds=20)
    disturbed[1260:1270] += 250
    flags = detect_artifacts(disturbed[None], 250, ("EEG",), window_s=1,
                             threshold_mad=8, flatline_tolerance_uv=0.15)
    flat = detect_artifacts(np.zeros((1, 1000)), 250, ("EEG",), window_s=2,
                            threshold_mad=8, flatline_tolerance_uv=0.15)
    clean_flags = detect_artifacts(sine(10, amplitude=5, seconds=20)[None], 250,
                                   ("EEG",), window_s=1, threshold_mad=8,
                                   flatline_tolerance_uv=0.15)
    checks["quality_controls"] = {
        "burst_flag_count": len(flags), "flatline_flag_count": len(flat),
        "clean_control_flag_count": len(clean_flags),
        "passed": bool(any(x["start_s"] <= 5 < x["end_s"] for x in flags)
                       and len(flat) == 2 and not clean_flags),
    }
    # Verify actual committed CSV sample inputs through the import and pipeline.
    sample_results = {}
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "examples/data/manifest.json").read_text(encoding="utf-8"))
    for filename, fs, modality in [("eeg_demo.csv", 250, "eeg"),
                                  ("emg_demo.csv", 2000, "emg")]:
        path = root / "examples" / "data" / filename
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["files"][filename]["sha256"]:
            raise ValueError(f"Sample checksum mismatch: {filename}")
        result = analyze(read_csv(path, sfreq=fs, modality=modality, time_column="time_s"))
        sample_results[filename] = {"channels": len(result.recording.channels),
                                    "duration_s": result.recording.duration_s,
                                    "artifact_candidates": len(result.artifact_intervals),
                                    "checksum_verified": True}

    recording = synthetic_recording(duration_s=60, sfreq=250, n_channels=8)
    analyze(recording)  # warm-up excluded
    timings = []
    for _ in range(5):
        start = time.perf_counter()
        analyze(recording)
        timings.append(time.perf_counter() - start)
    return {
        "schema_version": 1, "version": __version__,
        "assessment": "Numerical engineering checks on synthetic data; not clinical validation.",
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "dependencies": {name: importlib.metadata.version(name) for name in
                                         ["numpy", "scipy", "pandas", "mne", "streamlit", "plotly"]}},
        "checks": checks,
        "passed": all(item["passed"] for item in checks.values()),
        "sample_inputs": sample_results,
        "runtime_8ch_60s_250hz": {"repetitions": 5, "warmups": 1,
                                 "median_seconds": statistics.median(timings),
                                 "min_seconds": min(timings), "max_seconds": max(timings),
                                 "note": "Local timing, not a throughput guarantee."},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("verification-results.json"))
    args = parser.parse_args()
    result = verify()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Numerical checks: {sum(x['passed'] for x in result['checks'].values())}/"
          f"{len(result['checks'])}; results: {args.output}")
    sys.exit(0 if result["passed"] else 1)
