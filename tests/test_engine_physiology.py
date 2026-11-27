"""Synthetic peripheral pipeline checks; not clinical accuracy measurements."""

import json
import numpy as np
import pytest
from biosignal_lab.engine import Signal, process_peripheral


@pytest.fixture(scope="module")
def nk():
    return pytest.importorskip("neurokit2")


def test_ecg_pipeline_synthetic_rate_units_and_provenance(nk):
    values = nk.ecg_simulate(
        duration=20, sampling_rate=250, heart_rate=60, noise=0, method="simple", random_state=42
    )
    signal = Signal(
        (values * 1000)[None],
        250,
        ("ECG",),
        "ecg",
        "uV",
        reference="synthetic_zero",
        metadata={"seed": 42},
    )
    result = process_peripheral(signal, channel="ECG")
    summary = result.summary()
    assert summary["provenance"]["processing_unit"] == "mV"
    np.testing.assert_allclose(result.signals["ECG_Raw"], values)
    assert len(result.signals) == len(values) and "ECG_R_Peaks" in result.info
    assert summary["rate_descriptions"]["ECG_Rate"]["median_per_min"] == pytest.approx(60, abs=2)
    assert summary["provenance"]["input_data_sha256"]
    json.dumps(summary, allow_nan=False)


def test_ppg_pipeline_synthetic_rate_and_no_voltage_assumption(nk):
    values = nk.ppg_simulate(
        duration=30,
        sampling_rate=100,
        heart_rate=60,
        frequency_modulation=0,
        ibi_randomness=0,
        motion_amplitude=0,
        powerline_amplitude=0,
        random_state=42,
    )
    result = process_peripheral(Signal(values[None], 100, ("PPG",), "ppg", "a.u."), channel="PPG")
    assert "PPG_Peaks" in result.info
    assert result.summary()["rate_descriptions"]["PPG_Rate"]["median_per_min"] == pytest.approx(
        60, abs=2
    )
    with pytest.raises(ValueError, match="Incompatible"):
        process_peripheral(Signal(values[None], 100, ("PPG",), "ppg", "uV"), channel="PPG")


def test_eda_pipeline_preserves_conductance_and_unavailable_features(nk):
    values = nk.eda_simulate(duration=30, sampling_rate=100, scr_number=3, noise=0, random_state=42)
    result = process_peripheral(
        Signal((values * 1e-6)[None], 100, ("EDA",), "eda", "S"), channel="EDA"
    )
    np.testing.assert_allclose(result.signals["EDA_Raw"], values)
    assert {"EDA_Tonic", "EDA_Phasic", "SCR_Peaks"}.issubset(result.signals.columns)
    assert result.provenance["processing_unit"] == "uS"
    json.dumps(result.summary(), allow_nan=False)


def test_eog_pipeline_on_mathematical_positive_blink_pulses(nk):
    sfreq, duration = 100, 30
    time = np.arange(sfreq * duration) / sfreq
    # Mathematical bell pulses, not a claim of realistic blink morphology.
    values = sum(np.exp(-0.5 * ((time - event) / 0.08) ** 2) for event in [3, 8, 13, 18, 23, 28])
    signal = Signal(values[None], sfreq, ("VEOG",), "eog", "mV")
    result = process_peripheral(signal, channel="VEOG")
    assert "EOG_Blinks" in result.signals and len(result.signals) == len(values)
    peaks = result.info["EOG_Blinks"]
    assert len(peaks) >= 4
    assert all(np.min(abs(peaks / sfreq - target)) < 0.15 for target in [8, 13, 18, 23])
    json.dumps(result.summary(), allow_nan=False)


def test_invalid_peripheral_inputs_fail_explicitly(nk):
    with pytest.raises(ValueError, match="Constant"):
        process_peripheral(Signal(np.ones((1, 2000)), 100, ("ECG",), "ecg"), channel="ECG")
    with pytest.raises(ValueError, match="sample rate"):
        process_peripheral(Signal(np.arange(1000)[None], 50, ("ECG",), "ecg"), channel="ECG")
    with pytest.raises(ValueError, match="Select"):
        process_peripheral(Signal(np.arange(2000)[None], 100, ("EEG",)), channel="EEG")
