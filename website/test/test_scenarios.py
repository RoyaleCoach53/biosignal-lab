"""Check the serialized public demo against direct engine calls."""
import json
from itertools import product
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from scenarios import DESTINATION, calculate


MODES = [
    *product(("eeg",), ("clean", "burst"), ("standard", "high")),
    *product(("emg",), ("normal", "strong"), ("standard", "low")),
]


@pytest.mark.parametrize(("modality", "level", "preset"), MODES)
def test_catalogue_round_trips_engine(modality, level, preset):
    generated = json.loads((DESTINATION / f"{modality}-{level}-{preset}.json").read_text())
    rec, result = calculate(modality, level, preset)
    assert generated["provenance"] == "synthetic"
    assert generated["config"] == result.config.__dict__
    assert generated["sfreq"] == rec.sfreq
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
        assert channel["candidates"] == [row for row in result.artifact_intervals if row["channel"] == channel["name"]]
