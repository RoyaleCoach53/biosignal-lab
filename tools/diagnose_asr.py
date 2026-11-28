"""Optional synthetic ASRpy compatibility diagnostic; never a physiological validation.

Install the reviewed external ASRpy version separately to run this diagnostic.
It does not vendor, patch, auto-correct or expose ASR as an available engine method.
"""

from __future__ import annotations
import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import traceback
import numpy as np


def diagnose():
    report = {
        "schema_version": 1,
        "scope": "Synthetic compatibility diagnostic only; no physiological or clinical evidence",
        "fixture": {"seed": 42, "sfreq_hz": 250.0, "duration_s": 60.0, "n_channels": 4},
        "requested_method": "euclid",
        "cutoff": 20.0,
        "source_review": {
            "upstream": "https://github.com/DiGyt/asrpy",
            "license": "BSD-3-Clause",
            "reviewed_version": "0.0.8",
            "verified_pypi_wheel_sha256": "f0acf5f0c00513cfba60c38d5823424bcad3035f3ddee0c1272b638d4ed20384",
        },
    }
    try:
        import asrpy
        import asrpy.asr
        import mne
    except ImportError:
        report.update(status="dependency_unavailable", completed=False)
        return report, 2
    report["software"] = {
        name: metadata.version(name) for name in ("asrpy", "numpy", "scipy", "mne")
    }
    report["installed_asr_source_sha256"] = hashlib.sha256(
        Path(asrpy.asr.__file__).read_bytes()
    ).hexdigest()
    rng = np.random.default_rng(42)
    time = np.arange(15000) / 250.0
    # Mathematical oscillators/noise are not a user-reviewed physiological calibration.
    data = 1e-6 * (
        rng.normal(size=(4, len(time)))
        + np.array([np.sin(2 * np.pi * f * time) for f in [7, 10, 12, 17]])
    )
    report["fixture_data_sha256"] = hashlib.sha256(data.tobytes()).hexdigest()
    raw = mne.io.RawArray(
        data, mne.create_info(["A", "B", "C", "D"], 250.0, "eeg"), verbose="ERROR"
    )
    try:
        model = asrpy.ASR(sfreq=250.0, cutoff=20, method="euclid")
        model.fit(raw)
        values = model.transform(raw).get_data()
        if values.shape != data.shape or not np.all(np.isfinite(values)):
            raise ValueError("ASR returned unexpected shape or nonfinite samples")
        report.update(
            status="synthetic_compatibility_only", completed=True, output_shape=list(values.shape)
        )
        return report, 0
    except Exception as error:  # Diagnostic must report external implementation failures.
        frames = [
            {
                "module_file": "/".join(Path(frame.filename).parts[-2:]),
                "line": frame.lineno,
                "function": frame.name,
                "code": frame.line,
            }
            for frame in traceback.extract_tb(error.__traceback__)
        ]
        report.update(
            status="incompatible",
            completed=False,
            exception_type=type(error).__name__,
            exception_message=str(error),
            frames=frames,
        )
        return report, 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists() or args.output.is_symlink():
        parser.error("Output exists; select a new diagnostic report path")
    report, code = diagnose()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2, allow_nan=False)
        output.write("\n")
    print(json.dumps(report, indent=2, allow_nan=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
