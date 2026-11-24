"""Build the fixed synthetic catalogue with the BioSignal Lab Python engine."""
from dataclasses import replace
from importlib.metadata import version
from itertools import product
from pathlib import Path
import argparse
import json

from biosignal_lab import __version__
from biosignal_lab.pipeline import analyze, default_config
from biosignal_lab.simulate import synthetic_recording

DESTINATION = Path(__file__).resolve().parents[1] / "public" / "scenarios"
SEED = 42
DURATION = 12


def calculate(mode, level, preset):
    if mode == "eeg":
        recording = synthetic_recording(duration_s=DURATION, sfreq=250, seed=SEED,
                                        modality=mode, n_channels=8,
                                        with_artifacts=level == "burst")
        config = default_config(mode, recording.sfreq)
        if preset == "high":
            config = replace(config, highpass_hz=1)
    else:
        recording = synthetic_recording(duration_s=DURATION, sfreq=1000, seed=SEED,
                                        modality="emg", n_channels=1, with_artifacts=False)
        if level == "strong":
            recording = replace(recording, data_uv=recording.data_uv * 2)
        config = default_config(mode, recording.sfreq)
        if preset == "low":
            config = replace(config, lowpass_hz=120)
    return recording, analyze(recording, config)


def scenario(mode, level, preset):
    rec, result = calculate(mode, level, preset)
    # Preserve every sample of a 1 s illustrative excerpt. All 12 s enter analysis.
    start = int(4.5 * rec.sfreq)
    view = slice(start, start + int(rec.sfreq))
    channels = []
    for i, name in enumerate(rec.channels):
        channels.append({
            "name": name,
            "raw": rec.data_uv[i, view].tolist(),
            "processed": result.processed_uv[i, view].tolist(),
            "rawPsd": result.raw_psd_uv2_per_hz[i].tolist(),
            "psd": result.psd_uv2_per_hz[i].tolist(),
            "bands": [row for row in result.band_powers if row["channel"] == name],
            "rawQuality": result.raw_channel_metrics[i],
            "quality": result.channel_metrics[i],
            "candidates": [x for x in result.artifact_intervals if x["channel"] == name],
        })
    return {
        "mode": mode, "level": level, "preset": preset, "seed": SEED,
        "duration": DURATION, "sfreq": rec.sfreq, "start": start / rec.sfreq,
        "engine": __version__, "numpy": version("numpy"), "scipy": version("scipy"),
        "provenance": "synthetic", "config": result.config.__dict__,
        "freqs": result.frequencies_hz.tolist(), "warnings": result.warnings,
        "channels": channels,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DESTINATION)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for mode, levels, filters in (
        ("eeg", ("clean", "burst"), ("standard", "high")),
        ("emg", ("normal", "strong"), ("standard", "low")),
    ):
        for level, preset in product(levels, filters):
            payload = scenario(mode, level, preset)
            target = args.output / f"{mode}-{level}-{preset}.json"
            target.write_text(json.dumps(payload, allow_nan=False, separators=(",", ":")),
                              encoding="utf-8")


if __name__ == "__main__":
    main()
