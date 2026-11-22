"""Regenerate small synthetic samples; no human recordings are used."""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

from biosignal_lab.simulate import synthetic_recording


def main():
    directory = Path(__file__).resolve().parent / "data"
    directory.mkdir(exist_ok=True)
    manifest = {"license": "MIT", "origin": "synthetic_recording, seed 42; no human data",
                "generator": "examples/generate_samples.py", "files": {}}
    for name, modality, fs, duration, channels in [
        ("eeg_demo.csv", "eeg", 250, 10, 2), ("emg_demo.csv", "emg", 2000, 5, 1)
    ]:
        recording = synthetic_recording(modality=modality, sfreq=fs, duration_s=duration,
                                        n_channels=channels, seed=42, with_artifacts=True)
        frame = pd.DataFrame(recording.data_uv.T, columns=recording.channels)
        frame.insert(0, "time_s", np.arange(frame.shape[0]) / fs)
        path = directory / name
        frame.to_csv(path, index=False, float_format="%.10f", lineterminator="\n")
        manifest["files"][name] = {
            "modality": modality, "sampling_rate_hz": fs, "duration_s": duration,
            "amplitude_unit": "microvolts", "time_unit": "seconds",
            "channels": list(recording.channels), "samples_per_channel": frame.shape[0],
            "seed": 42, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(manifest['files'])} synthetic sample CSV files.")


if __name__ == "__main__":
    main()
