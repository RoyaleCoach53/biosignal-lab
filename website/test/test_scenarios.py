"""Verify the static, synthetic catalogue against the Python pipeline."""
import json
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.signal.windows import hann

from biosignal_lab.analysis import time_frequency_psd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from scenarios import DESTINATION, calculate, combinations


def read(name):
    return json.loads((DESTINATION / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(("modality", "level", "preset", "rate"), list(combinations()))
def test_catalogue_round_trips_engine(modality, level, preset, rate):
    name = f"{modality}-{level}-{preset}-{rate}"
    generated = read(name)
    spec = read(name + "-spectrogram")
    rec, result = calculate(modality, level, preset, rate)
    assert generated["provenance"] == spec["provenance"] == "synthetic"
    assert generated["config"] == result.config.__dict__
    assert generated["sfreq"] == rec.sfreq == rate
    assert len(generated["channels"]) == (8 if modality == "eeg" else 1)
    assert generated["warnings"] == result.warnings
    np.testing.assert_array_equal(generated["freqs"], result.frequencies_hz)
    for i, channel in enumerate(generated["channels"]):
        start = int(4.5 * rec.sfreq)
        end = start + int(rec.sfreq)
        assert channel["name"] == rec.channels[i]
        np.testing.assert_array_equal(channel["raw"], rec.data_uv[i, start:end])
        np.testing.assert_array_equal(channel["processed"], result.processed_uv[i, start:end])
        np.testing.assert_array_equal(channel["psd"], result.psd_uv2_per_hz[i])
        np.testing.assert_array_equal(channel["rawPsd"], result.raw_psd_uv2_per_hz[i])
        assert channel["rawQuality"] == result.raw_channel_metrics[i]
        assert channel["quality"] == result.channel_metrics[i]
        assert channel["bands"] == result.band_powers[i:i+1]
        assert channel["candidates"] == [row for row in result.artifact_intervals
                                         if row["channel"] == channel["name"]]
        frequency, time, power = time_frequency_psd(result.processed_uv[i], rate,
                                                     2 if modality == "eeg" else 1)
        keep = frequency <= (60 if modality == "eeg" else 400)
        np.testing.assert_array_equal(spec["freqs"], frequency[keep])
        np.testing.assert_array_equal(spec["times"], time)
        np.testing.assert_array_equal(spec["density"][i], power[keep])


def test_story_uses_engine_data_and_welch_mean():
    example = read("story")
    assert example["provenance"] == "synthetic"
    main = read("eeg-burst-standard-250")
    assert example["eeg"]["raw"] == [channel["raw"] for channel in main["channels"]]
    assert example["eeg"]["processed"] == [channel["processed"] for channel in main["channels"]]
    for preset, trace in example["eeg"]["filters"].items():
        assert trace == read(f"eeg-burst-{preset}-250")["channels"][0]["processed"]
    _, result = calculate("eeg", "burst", "standard", 250)
    step = example["welch"]
    segment = result.processed_uv[0, :1000]
    np.testing.assert_array_equal(step["segment"], segment)
    np.testing.assert_array_equal(step["windowed"], (segment - segment.mean()) * hann(1000, sym=False))
    np.testing.assert_allclose(np.mean(step["periodograms"], axis=0), step["average"], rtol=1e-12, atol=1e-14)
    assert example["emg"]["processed"] == read("emg-normal-standard-1000")["channels"][0]["processed"]
