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
        "passed": bool(np.all(diff <= limit)),
        "max_absolute_error_uv2_per_hz": float(np.max(diff)),
        "failing_bins": int(np.count_nonzero(diff > limit)),
        "bins_compared": int(diff.size),
        "rtol": PSD_RTOL,
        "atol_uv2_per_hz": PSD_ATOL,
        "note": "Matched processed samples; MNE and SciPy may share numerical algorithms.",
    }


def locate_recording(data_dir: Path, subject: int, run: int, download: bool) -> Path:
    name = f"S{subject:03d}R{run:02d}.edf"
    if download:
        paths = mne.datasets.eegbci.load_data(
            subjects=[subject], runs=[run], path=str(data_dir), verbose="ERROR"
        )
        if len(paths) != 1:
            raise ValueError(f"Expected exactly one file for {name}")
        return Path(paths[0])
    candidates = sorted(data_dir.rglob(name)) if data_dir.exists() else []
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"Expected one cached {name} under {data_dir}, found {len(candidates)}. "
            "Use --download to opt in to retrieval."
        )
    return candidates[0]


def evaluate_file(path: Path, subject: int, run: int) -> dict:
    recording = read_edf(path, modality="eeg", max_duration_s=None)
    if not np.isclose(recording.sfreq, EXPECTED_SFREQ, rtol=0, atol=1e-6):
        raise ValueError(f"Unexpected sampling rate: {recording.sfreq} Hz")
    if len(recording.channels) != EXPECTED_EEG_CHANNELS:
        raise ValueError(f"Unexpected EEG channel count: {len(recording.channels)}")
    if not np.all(np.isfinite(recording.data_uv)):
        raise ValueError("Non-finite input: inspect missing-data handling before analysis")

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
    parser.add_argument("--data-dir", type=Path, default=Path("local-results/physionet-cache"))
    parser.add_argument("--output", type=Path, default=Path("local-results/physionet-pilot.json"))
    parser.add_argument("--download", action="store_true",
                        help="Explicitly download EDF data from PhysioNet if needed")
    args = parser.parse_args(argv)
    if any(s < 1 or s > 109 for s in args.subjects):
        parser.error("Subjects must be between 1 and 109")
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
                    "error": f"{type(exc).__name__}: {exc}",
                })

    passed = len(records) == len(args.subjects) * len(args.runs) and all(
        item["passed"] for item in records
    )
    payload = {
        "schema_version": 1,
        "protocol": "PhysioNet EEGMMIDB eyes-open/eyes-closed baseline interoperability pilot",
        "dataset": DATASET_URL,
        "doi": DATASET_DOI,
        "dataset_license": "Open Data Commons Attribution License v1.0",
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
