"""Checksum-pinned, real-EEG numerical validation. No human waveforms are exported."""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import urllib.request

import mne
import numpy as np
from scipy.signal import iirnotch

from biosignal_lab.analysis import compute_psd, detect_artifacts
from biosignal_lab.io import read_edf
from biosignal_lab.models import AnalysisConfig, Recording
from biosignal_lab.pipeline import analyze

HERE = Path(__file__).resolve().parent
DATASET_BASE = "https://physionet.org/files/eegmmidb/1.0.0/"
BANDS = {"delta": (0.5, 4), "theta": (4, 8), "alpha": (8, 13),
         "beta": (13, 30), "gamma": (30, 45)}


def validate_manifest(manifest, protocol):
    expected = {f"S{s:03}R{int(r):02}" for s in protocol["subjects"] for r in protocol["runs"]}
    records = manifest["records"]
    if len(records) != len(expected) or {x["id"] for x in records} != expected:
        raise ValueError("Manifest must contain every protocol recording exactly once")
    for record in records:
        if record["id"] != f"S{record['subject']:03}R{record['run']:02}" or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"]):
            raise ValueError("Invalid manifest identity or checksum")
        if record["path"] != f"S{record['subject']:03}/{record['id']}.edf" or record["condition"] != protocol["runs"][str(record["run"])]:
            raise ValueError("Manifest path or condition disagrees with protocol")


def fetch_record(record: dict, cache: Path, download: bool) -> Path:
    relative = record["path"]
    if not re.fullmatch(r"S\d{3}/S\d{3}R\d{2}\.edf", relative):
        raise ValueError("Unexpected dataset path")
    if record["url"] != DATASET_BASE + relative:
        raise ValueError("Only the pinned official PhysioNet source is supported")
    path = cache / relative
    if not path.resolve().is_relative_to(cache.resolve()):
        raise ValueError("Cache path escapes its directory")
    if not path.exists():
        if not download:
            raise FileNotFoundError(f"Missing {relative}; use --download to fetch the protocol subset")
        with urllib.request.urlopen(record["url"], timeout=90) as response:
            content = response.read(8_000_001)
        if len(content) > 8_000_000:
            raise ValueError("Recording exceeds the subset download size limit")
        if hashlib.sha256(content).hexdigest() != record["sha256"]:
            raise ValueError(f"Official checksum mismatch: {relative}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
        raise ValueError(f"Cached recording checksum mismatch: {relative}; cache was not overwritten")
    return path


def decode_uniform_edf(path: Path, seconds: float | None = 60) -> tuple[np.ndarray, float, tuple[str, ...]]:
    """Independent digital-to-physical EDF decoder for this uniform-rate subset only.

    Not a general EDF/EDF+ replacement. Annotation channels and header personal
    fields are ignored. Mixed rates and discontinuous files are rejected.
    """
    blob = path.read_bytes()
    if len(blob) < 256 or blob[:8].strip() != b"0":
        raise ValueError("Unsupported EDF header")
    header_bytes, records = int(blob[184:192]), int(blob[236:244])
    record_seconds, count = float(blob[244:252]), int(blob[252:256])
    if count < 1 or records < 1 or record_seconds <= 0 or header_bytes != 256 + 256 * count:
        raise ValueError("Invalid EDF dimensions")
    if b"EDF+D" in blob[192:236]:
        raise ValueError("Discontinuous EDF is outside this benchmark")
    offset = 256
    fields = []
    for width in [16, 80, 8, 8, 8, 8, 8, 80, 8, 32]:
        fields.append([blob[offset + i * width:offset + (i + 1) * width].decode("ascii").strip()
                       for i in range(count)])
        offset += width * count
    samples = np.array([int(x) for x in fields[8]])
    picks = [i for i, label in enumerate(fields[0]) if label != "EDF Annotations"]
    if not picks or len(set(samples[picks])) != 1 or np.any(samples <= 0):
        raise ValueError("Only uniform-rate EEG is supported by the independent decoder")
    if len(blob) != header_bytes + records * int(samples.sum()) * 2:
        raise ValueError("EDF data length mismatch")
    digital = np.frombuffer(blob, dtype="<i2", offset=header_bytes).reshape(records, int(samples.sum()))
    fs = float(samples[picks[0]] / record_seconds)
    wanted = records * samples[picks[0]] if seconds is None else min(int(round(seconds * fs)), records * samples[picks[0]])
    starts = np.r_[0, np.cumsum(samples)]
    rows = []
    for i in picks:
        unit = fields[2][i].lower()
        if unit not in {"uv", "mv", "v"}:
            raise ValueError("Unexpected physical dimension in EDF benchmark")
        pmin, pmax = float(fields[3][i]), float(fields[4][i])
        dmin, dmax = int(fields[5][i]), int(fields[6][i])
        if not pmax > pmin or not dmax > dmin:
            raise ValueError("Invalid EDF physical scaling")
        values = digital[:, starts[i]:starts[i + 1]].reshape(-1)[:wanted].astype(float)
        physical = pmin + (values - dmin) * ((pmax - pmin) / (dmax - dmin))
        rows.append(physical * {"uv": 1, "mv": 1000, "v": 1e6}[unit])
    return np.array(rows), fs, tuple(fields[0][i] for i in picks)


def reference_filter(values_uv: np.ndarray, fs: float, config: AnalysisConfig,
                     native_padding: bool = False) -> np.ndarray:
    """Configure MNE independently from explicit protocol settings, in volts.

    Matched mode specifies SciPy-equivalent padding; native mode intentionally
    lets MNE estimate its own padding as a sensitivity analysis, not a gate.
    """
    values = values_uv * 1e-6
    values = values - values.mean(axis=1, keepdims=True)
    if config.notch_hz is not None:
        b, a = iirnotch(config.notch_hz, config.notch_quality, fs=fs)
        params = {"b": b, "a": a}
        if not native_padding:
            params["padlen"] = 3 * max(len(a), len(b))
        values = mne.filter.notch_filter(values, fs, [config.notch_hz], method="iir",
                                         iir_params=params, phase="zero", verbose="ERROR")
    if config.highpass_hz is not None or config.lowpass_hz is not None:
        params = {"order": 4, "ftype": "butter", "output": "sos"}
        if not native_padding:
            # Fourth-order high/low pass: two SOS; bandpass: four SOS.
            params["padlen"] = 27 if config.highpass_hz and config.lowpass_hz else 15
        values = mne.filter.filter_data(values, fs, config.highpass_hz, config.lowpass_hz,
                                        method="iir", iir_params=params, phase="zero", verbose="ERROR")
    return values * 1e6


def reference_psd(values_uv: np.ndarray, fs: float, window: float):
    n = min(values_uv.shape[1], max(16, round(fs * window)))
    power, frequencies = mne.time_frequency.psd_array_welch(
        values_uv * 1e-6, fs, n_fft=n, n_per_seg=n, n_overlap=n // 2,
        window="hann", average="mean", remove_dc=True, verbose="ERROR")
    return frequencies, power * 1e12


def integrate_linear(frequencies, densities, low, high):
    """Independent area of the linearly interpolated PSD, including band edges."""
    low, high = max(low, float(frequencies[0])), min(high, float(frequencies[-1]))
    points = np.r_[low, frequencies[(frequencies > low) & (frequencies < high)], high]
    values = np.array([np.interp(points, frequencies, row) for row in densities])
    return np.sum((values[:, 1:] + values[:, :-1]) * np.diff(points) / 2, axis=1)


def relative_l2(actual, expected):
    return float(np.linalg.norm(actual - expected) / max(float(np.linalg.norm(expected)), 1e-30))


def validate_record(record, path, protocol):
    rec = read_edf(path, max_duration_s=protocol["analysis_seconds"])
    independent, fs, labels = decode_uniform_edf(path, protocol["analysis_seconds"])
    cfg = AnalysisConfig(**protocol["primary_config"])
    result = analyze(rec, cfg)
    reference = reference_filter(independent, fs, cfg)
    frequencies, power = reference_psd(reference, fs, cfg.window_s)
    bands = {name: integrate_linear(frequencies, power, *edges) for name, edges in BANDS.items()}
    imported_error = float(np.max(np.abs(rec.data_uv - independent)))
    raw_f, raw_p = compute_psd(rec.data_uv, fs, cfg.window_s)
    raw_ref_f, raw_ref_p = reference_psd(independent, fs, cfg.window_s)
    band_error = max(float(np.max(np.abs(np.array([row[name + "_uv2"] for row in result.band_powers])
                                         - target) / np.maximum(np.abs(target), 1e-12)))
                     for name, target in bands.items())
    qc_reference = {
        "rms_uv": np.sqrt(np.mean(reference ** 2, axis=1)), "std_uv": np.std(reference, axis=1),
        "peak_to_peak_uv": np.ptp(reference, axis=1), "median_uv": np.median(reference, axis=1),
    }
    qc_error = max(float(np.max(np.abs(np.array([row[key] for row in result.channel_metrics]) - target)))
                   for key, target in qc_reference.items())
    errors = {"units_max_abs_uv": imported_error,
              "waveform_relative_l2": relative_l2(result.processed_uv, reference),
              "raw_psd_relative_l2": relative_l2(raw_p, raw_ref_p),
              "psd_relative_l2": relative_l2(result.psd_uv2_per_hz, power),
              "band_relative_error": band_error, "rounded_qc_max_abs_uv": qc_error}
    limits = protocol["primary_tolerances"]
    passed = (fs == 160 and rec.sfreq == fs and len(labels) == 64 and rec.channels == labels
              and independent.shape == (64, 9600)
              and np.array_equal(frequencies, result.frequencies_hz) and np.array_equal(raw_f, raw_ref_f)
              and all(np.all(np.isfinite(x)) for x in [result.processed_uv, power, raw_p])
              and all(errors[k] <= v for k, v in limits.items())
              and errors["raw_psd_relative_l2"] <= limits["psd_relative_l2"])
    sensitivity = {}
    base_rms = np.sqrt(np.mean(result.processed_uv ** 2, axis=1))
    for name, candidate in [("highpass_1hz", replace(cfg, highpass_hz=1.0)),
                            ("lowpass_40hz", replace(cfg, lowpass_hz=40.0)),
                            ("no_notch", replace(cfg, notch_hz=None))]:
        alt = analyze(rec, candidate)
        sensitivity[name] = {
            "median_rms_ratio": float(np.median(np.sqrt(np.mean(alt.processed_uv ** 2, axis=1)) / base_rms)),
            "median_delta_power_ratio": float(np.median([a["delta_uv2"] / b["delta_uv2"]
                                                          for a, b in zip(alt.band_powers, result.band_powers)])),
            "median_gamma_power_ratio": float(np.median([a["gamma_uv2"] / b["gamma_uv2"]
                                                          for a, b in zip(alt.band_powers, result.band_powers)])),
        }
    native = reference_filter(independent, fs, cfg, native_padding=True)
    trim = round(fs * protocol["sensitivity"]["edge_exclusion_s"])
    sensitivity["mne_native_padding"] = {
        "whole_record_relative_l2": relative_l2(result.processed_uv, native),
        "interior_relative_l2": relative_l2(result.processed_uv[:, trim:-trim], native[:, trim:-trim]),
        "qualification": "Different edge policies; not an equivalence gate or physiological ground truth.",
    }
    for window in protocol["sensitivity"]["welch_windows_s"]:
        f, p = compute_psd(result.processed_uv, fs, window)
        rf, rp = reference_psd(reference, fs, window)
        error = relative_l2(p, rp)
        passed = bool(passed and np.array_equal(f, rf) and error <= limits["psd_relative_l2"])
        sensitivity[f"welch_{window}s"] = {
            "reference_relative_l2": error,
            "median_alpha_uv2": float(np.median(integrate_linear(f, p, 8, 13))),
            "median_delta_uv2": float(np.median(integrate_linear(f, p, 0.5, 4))),
        }
    # Known corruptions superimposed on one real channel; no expert artifact labels.
    perturbed = rec.data_uv[:1].copy()
    perturbed[0, 5 * int(fs):6 * int(fs)] = 0
    perturbed[0, 10 * int(fs):10 * int(fs) + 10] += 1e6
    flags = detect_artifacts(perturbed, fs, labels[:1], window_s=1, threshold_mad=8, flatline_tolerance_uv=.15)
    flat_found = any(x["start_s"] == 5 and "flatline" in x["reason"] for x in flags)
    burst_found = any(x["start_s"] == 10 and "outlier" in x["reason"] for x in flags)
    gapped = rec.data_uv[:1].copy()
    gapped[0, 100:103] = np.nan
    repaired = analyze(Recording(gapped, fs, labels[:1]), cfg)
    short_gap_ok = bool(np.all(np.isfinite(repaired.processed_uv)) and any("interpolated" in x for x in repaired.warnings))
    rejected = {}
    for name, start, end in [("long_gap", 100, 132), ("boundary_gap", 0, 1)]:
        damaged = rec.data_uv[:1].copy()
        damaged[0, start:end] = np.nan
        try:
            analyze(Recording(damaged, fs, labels[:1]), cfg)
            rejected[name] = False
        except ValueError:
            rejected[name] = True
    passed = bool(passed and flat_found and burst_found and short_gap_ok and all(rejected.values()))
    return {"id": record["id"], "subject": record["subject"], "condition": record["condition"],
            "sha256": record["sha256"], "samples_per_channel": 9600, "channels": len(labels),
            "sfreq_hz": fs, "passed": passed, "errors": errors,
            "natural_artifact_candidate_count": len(result.artifact_intervals),
            "quality_controls": {"injected_flatline_detected": flat_found, "injected_burst_detected": burst_found},
            "missing_data_controls": {"short_gap_finite_and_disclosed": short_gap_ok, **rejected},
            "median_channel_rms_uv": float(np.median(base_rms)),
            "median_channel_alpha_uv2": float(np.median(bands["alpha"])),
            "sensitivity": sensitivity, "warnings": result.warnings}


def run(cache: Path, download: bool, output: Path):
    if cache.resolve().is_relative_to(HERE.parents[1]):
        raise ValueError("Keep human recordings outside the repository")
    protocol_bytes = (HERE / "protocol.json").read_bytes()
    protocol = json.loads(protocol_bytes)
    manifest_bytes = (HERE / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    validate_manifest(manifest, protocol)
    records, failures = [], []
    for record in manifest["records"]:
        try:
            result = validate_record(record, fetch_record(record, cache, download), protocol)
            records.append(result)
            print(record["id"], "PASS" if result["passed"] else "FAIL", flush=True)
        except Exception as exc:
            # Retain each failed ID and exception type without copying EDF headers or local paths.
            failures.append({"id": record["id"], "error_type": type(exc).__name__})
            print(record["id"], type(exc).__name__, flush=True)
    report = {"protocol_version": protocol["protocol_version"], "protocol_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
              "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(), "dataset": manifest["dataset"],
              "dataset_url": manifest["dataset_url"], "license_url": manifest["license_url"],
              "attribution": manifest["attribution"], "environment": {"python": platform.python_version(),
              "packages": {n: importlib.metadata.version(n) for n in ["biosignal-lab", "mne", "numpy", "scipy"]}},
              "records": records, "failures": failures,
              "passed": len(records) == 9 and not failures and all(x["passed"] for x in records),
              "interpretation": protocol["interpretation"]}
    source_root = HERE.parents[1]
    source_files = ["benchmarks/real_world/validate.py", "src/biosignal_lab/io.py",
                    "src/biosignal_lab/analysis.py", "src/biosignal_lab/preprocessing.py",
                    "src/biosignal_lab/pipeline.py", "src/biosignal_lab/models.py"]
    report["software_source_sha256"] = {name: hashlib.sha256((source_root / name).read_bytes()).hexdigest()
                                        for name in source_files}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8", newline="\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True, help="Outside-repository recording cache")
    parser.add_argument("--download", action="store_true", help="Download only the checksum-pinned official subset")
    parser.add_argument("--output", type=Path, default=Path("real-world-results.json"))
    args = parser.parse_args()
    if args.cache.resolve().is_relative_to(HERE.parents[1]):
        parser.error("Keep human recordings outside the repository")
    report = run(args.cache, args.download, args.output)
    print(f"Real EEG validation: {sum(x['passed'] for x in report['records'])}/9 records passed")
    raise SystemExit(0 if report["passed"] else 1)
