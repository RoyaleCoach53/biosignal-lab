"""Generate the synthetic console and scroll story from the Python engine."""
from dataclasses import replace
from importlib.metadata import version
from itertools import product
from pathlib import Path
import argparse
import json

import numpy as np
from scipy.signal.windows import hann

from biosignal_lab import __version__
from biosignal_lab.analysis import time_frequency_psd
from biosignal_lab.pipeline import analyze, default_config
from biosignal_lab.simulate import synthetic_recording

DESTINATION = Path(__file__).resolve().parents[1] / "public" / "scenarios"
SEED = 42
DURATION = 12
MODES = {
    "eeg": ((128, 250, 500), ("clean", "burst"), ("standard", "high", "low", "no-notch")),
    "emg": ((1000, 2000), ("normal", "strong"), ("standard", "low")),
}


def combinations():
    for mode, (rates, levels, presets) in MODES.items():
        for rate, level, preset in product(rates, levels, presets):
            yield mode, level, preset, rate


def calculate(mode, level, preset, rate):
    rates, levels, presets = MODES[mode]
    if rate not in rates or level not in levels or preset not in presets:
        raise ValueError("Scenario outside the published catalogue")
    recording = synthetic_recording(duration_s=DURATION, sfreq=rate, seed=SEED,
                                    modality=mode, n_channels=8 if mode == "eeg" else 1,
                                    with_artifacts=level == "burst")
    if mode == "emg" and level == "strong":
        recording = replace(recording, data_uv=recording.data_uv * 2)
    config = default_config(mode, recording.sfreq)
    if preset == "high":
        config = replace(config, highpass_hz=1)
    if preset == "low":
        config = replace(config, lowpass_hz=35 if mode == "eeg" else 120)
    if preset == "no-notch":
        config = replace(config, notch_hz=None)
    return recording, analyze(recording, config)


def export(recording, result, mode, level, preset):
    start = int(4.5 * recording.sfreq)
    view = slice(start, start + int(recording.sfreq))
    channels = []
    for i, name in enumerate(recording.channels):
        channels.append({
            "name": name, "raw": recording.data_uv[i, view].tolist(),
            "processed": result.processed_uv[i, view].tolist(),
            "rawPsd": result.raw_psd_uv2_per_hz[i].tolist(),
            "psd": result.psd_uv2_per_hz[i].tolist(),
            "bands": result.band_powers[i:i+1],
            "rawQuality": result.raw_channel_metrics[i],
            "quality": result.channel_metrics[i],
            "candidates": [x for x in result.artifact_intervals if x["channel"] == name],
        })
    return {
        "mode": mode, "level": level, "preset": preset, "seed": SEED,
        "duration": DURATION, "sfreq": recording.sfreq, "start": start / recording.sfreq,
        "engine": __version__, "numpy": version("numpy"), "scipy": version("scipy"),
        "provenance": "synthetic", "config": result.config.__dict__,
        "freqs": result.frequencies_hz.tolist(), "warnings": result.warnings,
        "channels": channels,
    }


def spectral_frames(recording, result):
    window = 2 if recording.modality == "eeg" else 1
    maximum = 60 if recording.modality == "eeg" else 400
    surfaces = []
    for signal in result.processed_uv:
        frequencies, times, values = time_frequency_psd(signal, recording.sfreq, window)
        keep = frequencies <= maximum
        surfaces.append(values[keep].tolist())
    return {"freqs": frequencies[keep].tolist(), "times": times.tolist(),
            "windowSeconds": window, "density": surfaces, "provenance": "synthetic"}


def story():
    eeg, result = calculate("eeg", "burst", "standard", 250)
    standard = export(eeg, result, "eeg", "burst", "standard")
    frame_len = int(result.config.window_s * eeg.sfreq)
    segment = result.processed_uv[0, :frame_len]
    freqs, _, periodograms = time_frequency_psd(result.processed_uv[0], eeg.sfreq,
                                               result.config.window_s)
    visible = freqs <= 60
    filters = {"standard": standard["channels"][0]["processed"]}
    for preset in ("high", "low", "no-notch"):
        _, different = calculate("eeg", "burst", preset, 250)
        start = int(standard["start"] * eeg.sfreq)
        filters[preset] = different.processed_uv[0, start:start+int(eeg.sfreq)].tolist()
    emg, emg_result = calculate("emg", "normal", "standard", 1000)
    emg_export = export(emg, emg_result, "emg", "normal", "standard")["channels"][0]
    return {
        "provenance": "synthetic", "eeg": {
            "raw": [c["raw"] for c in standard["channels"]],
            "processed": [c["processed"] for c in standard["channels"]],
            "filters": filters, "start": standard["start"], "rate": eeg.sfreq,
        },
        "welch": {
            "segment": segment.tolist(),
            "windowed": ((segment - segment.mean()) * hann(frame_len, sym=False)).tolist(),
            "freqs": freqs[visible].tolist(),
            "periodograms": periodograms[visible].T.tolist(),
            "average": result.psd_uv2_per_hz[0, visible].tolist(),
            "duration": result.config.window_s,
        },
        "emg": {"raw": emg_export["raw"], "processed": emg_export["processed"],
                "quality": emg_export["quality"], "rate": emg.sfreq},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DESTINATION)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    def write(name, value):
        (args.output / f"{name}.json").write_text(
            json.dumps(value, allow_nan=False, separators=(",", ":")), encoding="utf-8")

    for mode, level, preset, rate in combinations():
        source, result = calculate(mode, level, preset, rate)
        name = f"{mode}-{level}-{preset}-{rate}"
        write(name, export(source, result, mode, level, preset))
        write(f"{name}-spectrogram", spectral_frames(source, result))
    write("story", story())


if __name__ == "__main__":
    main()
