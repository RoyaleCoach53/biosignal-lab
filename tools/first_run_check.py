"""Offline first-use check. Prints shareable software facts, never recordings or paths."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import platform
import subprocess

import numpy as np

from biosignal_lab import __version__, analyze
from biosignal_lab.simulate import synthetic_recording

ROOT = Path(__file__).resolve().parents[1]


def source_revision(root: Path = ROOT):
    try:
        top = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=root,
                                      stderr=subprocess.DEVNULL, text=True).strip()
        if Path(top).resolve() != root.resolve():
            return None
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def source_state(root: Path = ROOT):
    if source_revision(root) is None:
        return "unavailable"
    output = subprocess.check_output(["git", "status", "--porcelain"], cwd=root,
                                     stderr=subprocess.DEVNULL, text=True)
    return "modified" if output.strip() else "clean"


def check(require_app=False, require_edf=False):
    result = analyze(synthetic_recording(n_channels=2, duration_s=10, seed=42))
    manifest = json.loads((ROOT / "examples/data/manifest.json").read_text(encoding="utf-8"))
    samples_ok = all(hashlib.sha256((ROOT / "examples/data" / name).read_bytes()).hexdigest() == record["sha256"]
                     for name, record in manifest["files"].items())
    available = {name: importlib.util.find_spec(name) is not None for name in ("streamlit", "plotly", "mne")}
    core_ok = bool(np.isfinite(result.processed_uv).all() and np.isfinite(result.psd_uv2_per_hz).all()
                   and (result.psd_uv2_per_hz >= 0).all() and len(result.band_powers) == 2)
    passed = core_ok and samples_ok and (not require_app or (available["streamlit"] and available["plotly"])) and (not require_edf or available["mne"])
    return {"schema_version": 1, "version": __version__, "source_revision": source_revision(), "source_state": source_state(),
            "python": platform.python_version(), "os": platform.system(), "architecture": platform.machine(),
            "packages": {name: importlib.metadata.version(name) for name in ("biosignal-lab", "numpy", "scipy", "pandas")},
            "optional_imports_available": available, "requirements": {"app": require_app, "edf": require_edf},
            "synthetic_seed": 42, "synthetic_finite_nonnegative_psd": core_ok,
            "synthetic_sample_hashes_verified": samples_ok, "passed": bool(passed),
            "scope": "Offline software smoke check, not clinical validation. Optional availability is not a full integration test. No human data, usernames or local paths included."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-app", action="store_true")
    parser.add_argument("--require-edf", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = check(args.require_app, args.require_edf)
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    print(text, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
