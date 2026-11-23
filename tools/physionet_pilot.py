"""Opt-in, auditable pilot for PhysioNet EEG Motor Movement/Imagery baseline EDF files.

This checks software interoperability on human recordings, NOT physiology or diagnosis.
No files are downloaded without --download, and no EDF data are committed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import mne
import numpy as np
import scipy

from biosignal_lab.io import read_edf
from biosignal_lab.models import AnalysisConfig
from biosignal_lab.pipeline import analyze

# Allow both `python tools/physionet_pilot.py` and module/test imports.
REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))
from benchmarks.real_world.validate import decode_uniform_edf, fetch_record

MANIFEST = json.loads((REPOSITORY / "benchmarks/real_world/manifest.json").read_text(encoding="utf-8"))


def pinned_record(subject: int, run: int) -> dict:
    for item in MANIFEST["records"]:
        if item["subject"] == subject and item["run"] == run and run in (1, 2):
            return item
    raise ValueError("This baseline pilot supports only checksum-pinned subjects 1, 2, 3 and runs 1, 2")

DATASET_URL = "https://physionet.org/content/eegmmidb/1.0.0/"
DATASET_DOI = "10.13026/C28G6P"
EXPECTED_SFREQ = 160.0
EXPECTED_EEG_CHANNELS = 64
PSD_RTOL = 1e-7
PSD_ATOL = 1e-10  # microvolts squared per Hz


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def compare_psd(result) -> dict:
    """Matched-setting numerical agreement, not an independent clinical reference."""
    nperseg = min(
        result.processed_uv.shape[1],
        max(16, int(round(result.recording.sfreq * result.config.window_s))),
    )
    reference_v2, reference_hz = mne.time_frequency.psd_array_welch(
        result.processed_uv * 1e-6,
        sfreq=result.recording.sfreq,
        n_fft=nperseg,
        n_per_seg=nperseg,
        n_overlap=nperseg // 2,
        window="hann",
        average="mean",
        remove_dc=True,
        verbose="ERROR",
    )
    reference_uv2 = reference_v2 * 1e12
    if reference_uv2.shape != result.psd_uv2_per_hz.shape:
        raise ValueError("MNE and BioSignal Lab PSD output shapes differ")
    if not np.array_equal(reference_hz, result.frequencies_hz):
        raise ValueError("MNE and BioSignal Lab frequency grids differ")
    if not np.all(np.isfinite(reference_uv2)) or not np.all(np.isfinite(result.psd_uv2_per_hz)):
        raise ValueError("Non-finite PSD values")
    diff = np.abs(result.psd_uv2_per_hz - reference_uv2)
    limit = PSD_ATOL + PSD_RTOL * np.abs(reference_uv2)
    return {
        "passed": bool(np.all(diff <= limit) and np.all(reference_uv2 >= 0) and np.all(result.psd_uv2_per_hz >= 0)),
        "negative_bins": int(np.count_nonzero(result.psd_uv2_per_hz < 0)),
        "max_absolute_error_uv2_per_hz": float(np.max(diff)),
        "failing_bins": int(np.count_nonzero(diff > limit)),
        "bins_compared": int(diff.size),
        "rtol": PSD_RTOL,
        "atol_uv2_per_hz": PSD_ATOL,
        "note": "Matched processed samples; MNE and SciPy may share numerical algorithms.",
    }


def locate_recording(data_dir: Path, subject: int, run: int, download: bool) -> Path:
    if data_dir.resolve().is_relative_to(REPOSITORY):
        raise ValueError("Human recording caches must be outside the repository")
    record = pinned_record(subject, run)
    name = f"S{subject:03d}R{run:02d}.edf"
    candidates = sorted(data_dir.rglob(name)) if data_dir.exists() else []
    if len(candidates) == 1:
        if sha256_file(candidates[0]) != record["sha256"]:
            raise ValueError(f"Official checksum mismatch for {name}; cached file was not overwritten")
        return candidates[0]
    if not candidates and download:
        return fetch_record(record, data_dir, True)
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"Expected one cached {name} under {data_dir}, found {len(candidates)}. "
            "Use --download to opt in to retrieval."
        )
    return candidates[0]


def evaluate_file(path: Path, subject: int, run: int) -> dict:
    expected = pinned_record(subject, run)
    if sha256_file(path) != expected["sha256"]:
        raise ValueError("Input checksum differs from official pinned recording")
    recording = read_edf(path, modality="eeg", max_duration_s=None)
    if not np.isclose(recording.sfreq, EXPECTED_SFREQ, rtol=0, atol=1e-6):
        raise ValueError(f"Unexpected sampling rate: {recording.sfreq} Hz")
    if len(recording.channels) != EXPECTED_EEG_CHANNELS:
        raise ValueError(f"Unexpected EEG channel count: {len(recording.channels)}")
    if not np.all(np.isfinite(recording.data_uv)):
        raise ValueError("Non-finite input: inspect missing-data handling before analysis")
    independent, independent_fs, independent_labels = decode_uniform_edf(path, seconds=None)
    if recording.channels != independent_labels or recording.sfreq != independent_fs or recording.data_uv.shape != independent.shape:
        raise ValueError("EDF metadata disagrees with independent digital decoder")
    units_error = float(np.max(np.abs(recording.data_uv - independent)))
    if units_error > 1e-8:
        raise ValueError("EDF digital-to-physical unit conversion mismatch")

    # Preserve delivered reference; no line-notch/high/low pass. Mean is removed
    # by the library's pipeline, and both PSD implementations see identical samples.
    config = AnalysisConfig(
        modality="eeg", highpass_hz=None, lowpass_hz=None,
        notch_hz=None, window_s=4.0
    )
    result = analyze(recording, config)
    psd_check = compare_psd(result)
    return {
        "subject": subject,
        "run": run,
        "run_label": {1: "eyes open baseline", 2: "eyes closed baseline"}[run],
        "filename": path.name,
        "source_sha256": sha256_file(path),
        "official_checksum_verified": True,
        "independent_edf_units_max_abs_uv": units_error,
        "sampling_hz": recording.sfreq,
        "channels": list(recording.channels),
        "samples": int(recording.data_uv.shape[1]),
        "duration_s": recording.duration_s,
        "processing": {
            "mean_removal": True,
            "software_highpass": None,
            "software_lowpass": None,
            "software_notch": None,
            "re_reference": False,
            "welch_window_s": 4.0,
            "window": "hann",
            "overlap_fraction": 0.5,
        },
        "psd_comparison": psd_check,
        "pipeline_warnings": result.warnings,
        "artifact_candidate_count_unvalidated": len(result.artifact_intervals),
        "passed": psd_check["passed"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subjects", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--runs", type=int, nargs="+", choices=[1, 2], default=[1, 2])
    parser.add_argument("--data-dir", type=Path, default=Path("../biosignal-lab-data"),
                        help="Outside-repository cache (older MNE nested caches remain readable)")
    parser.add_argument("--output", type=Path, default=Path("local-results/physionet-pilot.json"))
    parser.add_argument("--download", action="store_true",
                        help="Explicitly download EDF data from PhysioNet if needed")
    args = parser.parse_args(argv)
    if any(s not in (1, 2, 3) for s in args.subjects):
        parser.error("This frozen pilot supports checksum-pinned subjects 1, 2, 3 only")
    if len(set(args.subjects)) != len(args.subjects) or len(set(args.runs)) != len(args.runs):
        parser.error("Duplicate subjects or runs are not allowed")

    records = []
    for subject in args.subjects:
        for run in args.runs:
            try:
                path = locate_recording(args.data_dir, subject, run, args.download)
                records.append(evaluate_file(path, subject, run))
            except (OSError, ValueError, RuntimeError) as exc:
                records.append({
                    "subject": subject, "run": run, "passed": False,
                    "error": f"{type(exc).__name__}: recording unavailable or failed integrity/data checks",
                })

    passed = len(records) == len(args.subjects) * len(args.runs) and all(
        item["passed"] for item in records
    )
    payload = {
        "schema_version": 1,
        "runner_sha256": sha256_file(Path(__file__)),
        "independent_decoder_source_sha256": sha256_file(REPOSITORY / "benchmarks/real_world/validate.py"),
        "protocol": "PhysioNet EEGMMIDB eyes-open/eyes-closed baseline interoperability pilot",
        "dataset": DATASET_URL,
        "doi": DATASET_DOI,
        "dataset_license": "Open Data Commons Attribution License v1.0",
        "license_url": MANIFEST["license_url"],
        "attribution": MANIFEST["attribution"],
        "full_protocol_selection": set(args.subjects) == {1, 2, 3} and set(args.runs) == {1, 2},
        "subject_selection": args.subjects,
        "run_selection": args.runs,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "mne": mne.__version__,
        },
        "records": records,
        "passed": passed,
        "interpretation": "Technical interoperability pilot only; not human physiology, artifact-classifier, or clinical validation.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"{len(records)} cases; passed={passed}; report={args.output}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
