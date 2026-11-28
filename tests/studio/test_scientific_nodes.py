"""Analytical signals exercise scientific nodes and metadata semantics."""
from pathlib import Path

import numpy as np
import pytest

from biosignal_lab.studio import (Definition, Port, Node, Connection, Workflow,
                                  Executor, builtin_registry, NodeExecutionError, WorkflowError)
from biosignal_lab.studio.editor import clean_view_state


def source_registry(*, modality="eeg", samples=500):
    engine = pytest.importorskip("biosignal_lab.engine")
    t = np.arange(samples) / 100
    data = np.array([2 * np.sin(2 * np.pi * 10 * t), 3 * np.sin(2 * np.pi * 10 * t + .3)])
    signal = engine.Signal(data, 100, ("A", "B"), modality=modality, unit="uV", reference="synthetic_reference")
    registry = builtin_registry()
    registry.register(Definition("known", {}, {"out": Port("signal")}, lambda i, p, c: {"out": signal},
                                  lambda p: None, parallel_safe=True), trusted=True)
    return registry


def run(registry, *nodes):
    return Executor(registry, max_workers=4).execute(Workflow((Node("source", "known"), *nodes)))


def test_fft_psd_multitaper_band_integral_and_entropy_on_known_tone():
    registry = source_registry()
    execution = run(registry,
                    Node("fft", "fft", inputs={"signal": Connection("source")}),
                    Node("psd", "engine_psd", inputs={"signal": Connection("source")}),
                    Node("multitaper", "multitaper", {"time_bandwidth": 2, "n_tapers": 3}, {"signal": Connection("source")}),
                    Node("band", "band_power", {"low_hz": 8, "high_hz": 12}, {"spectrum": Connection("psd")}),
                    Node("entropy", "spectral_entropy", inputs={"spectrum": Connection("psd")}))
    fft = execution.outputs["fft"]["out"]
    index = fft["frequencies_hz"].index(10)
    np.testing.assert_allclose(np.array(fft["amplitude"])[:, index], [2, 3], atol=1e-12)
    np.testing.assert_allclose(execution.outputs["band"]["out"]["power"], [2, 4.5], rtol=1e-10)
    assert fft["unit"] == "uV" and execution.outputs["band"]["out"]["unit"] == "uV^2"
    spectrum = execution.outputs["multitaper"]["out"]
    np.testing.assert_allclose(np.trapezoid(spectrum["power"], spectrum["frequencies"], axis=-1), [2, 4.5], rtol=.02)
    entropy = execution.outputs["entropy"]["out"]
    assert all(0 <= value <= 1 for value in entropy["entropy"])


def test_stft_and_spectrogram_keep_different_calibrations_and_shapes():
    execution = run(source_registry(),
                    Node("stft", "stft", {"window_s": 1}, {"signal": Connection("source")}),
                    Node("spectrogram", "spectrogram", {"window_s": 1}, {"signal": Connection("source")}))
    coefficients, density = execution.outputs["stft"]["out"], execution.outputs["spectrogram"]["out"]
    assert np.array(coefficients["real"]).shape == (2, 51, 9)
    assert np.array(density["power"]).shape == (2, 51, 9)
    assert coefficients["unit"] == "uV" and density["unit"] == "uV^2/Hz"
    assert "not calibrated PSD" in coefficients["representation"]
    peak = np.array(density["power"])[0].mean(axis=1).argmax()
    assert density["frequencies_hz"][peak] == 10


def test_bipolar_plv_epoch_baseline_and_average_preserve_reference_and_events():
    execution = run(source_registry(),
                    Node("bipolar", "bipolar", {"pairs": [["A", "B"]]}, {"signal": Connection("source")}),
                    Node("plv", "plv", inputs={"signal": Connection("source")}),
                    Node("epochs", "epochs", {"events": [100, 200, 300], "tmin": -.2, "tmax": .2, "baseline": [-.2, 0]},
                         {"signal": Connection("source")}),
                    Node("evoked", "epoch_average", inputs={"epochs": Connection("epochs")}),
                    Node("epoch_info", "epoch_info", inputs={"epochs": Connection("epochs")}))
    bipolar = execution.outputs["bipolar"]["out"]
    assert bipolar.channels == ("A-B",) and bipolar.reference == "bipolar"
    np.testing.assert_allclose(execution.outputs["plv"]["out"]["matrix"], np.ones((2, 2)), atol=1e-12)
    epochs, evoked = execution.outputs["epochs"]["out"], execution.outputs["evoked"]["out"]
    assert epochs.data.shape == (3, 2, 41) and evoked.metadata["evoked_trials"] == 3
    np.testing.assert_allclose(evoked.data[:, epochs.times <= 0].mean(axis=1), 0, atol=1e-12)
    assert execution.outputs["epoch_info"]["out"]["events"] == [100, 200, 300]
    assert evoked.reference == "synthetic_reference"


def test_emg_descriptors_and_activation_use_real_signal_units():
    execution = run(source_registry(modality="emg"),
                    Node("features", "emg_features", inputs={"signal": Connection("source")}),
                    Node("activation", "emg_activation", {"threshold": 1, "window_s": .1, "min_duration_s": .1},
                         {"signal": Connection("source")}))
    features = execution.outputs["features"]["out"]
    np.testing.assert_allclose([row["rms"] for row in features], [np.sqrt(2), 3 / np.sqrt(2)], rtol=1e-12)
    assert all(row["amplitude_unit"] == "uV" for row in features)
    assert execution.outputs["activation"]["out"]


def test_wavelet_coefficients_are_not_mislabeled_as_spectral_density():
    pytest.importorskip("pywt")
    execution = run(source_registry(), Node("cwt", "wavelet", {"frequencies_hz": [5, 10, 20]},
                                           {"signal": Connection("source")}))
    coefficients = execution.outputs["cwt"]["out"]
    assert np.array(coefficients["real"]).shape == (3, 2, 500)
    assert "not calibrated PSD" in coefficients["representation"]
    assert coefficients["input_amplitude_unit"] == "uV"
    magnitude = abs(np.array(coefficients["real"]))[:, 0, 50:-50].mean(axis=1)
    assert magnitude[1] > magnitude[0] and magnitude[1] > magnitude[2]
    with pytest.raises(NodeExecutionError, match="200000-value budget"):
        run(source_registry(samples=8000), Node("large", "wavelet", inputs={"signal": Connection("source")}))


def test_ica_requires_explicit_review_and_real_mne_reconstruction():
    pytest.importorskip("mne")
    pytest.importorskip("sklearn")
    engine = pytest.importorskip("biosignal_lab.engine")
    with pytest.raises(WorkflowError, match="reviewed=true"):
        Executor(source_registry()).validate(Workflow((Node("source", "known"),
                                                       Node("ica", "ica", {"exclude": []}, {"signal": Connection("source")}))))
    t = np.arange(1000) / 100
    sources = np.vstack([np.sin(2 * np.pi * 10 * t), np.sign(np.sin(2 * np.pi * 2 * t))])
    signal = engine.Signal(np.array([[1., .4], [.2, 1.]]) @ sources, 100, ("A", "B"))
    registry = builtin_registry()
    registry.register(Definition("mixture", {}, {"out": Port("signal")}, lambda i, p, c: {"out": signal},
                                  lambda p: None), trusted=True)
    execution = Executor(registry).execute(Workflow((Node("source", "mixture"),
                                                    Node("ica", "ica", {"exclude": [], "reviewed": True, "n_components": 2, "max_iter": 1000},
                                                         {"signal": Connection("source")}))))
    result = execution.outputs["ica"]["out"]
    np.testing.assert_allclose(result.data, signal.data, atol=1e-12)
    assert result.history[-1]["parameters"]["exclude"] == []


def test_real_subject_grouped_csp_and_covariance_nodes():
    pytest.importorskip("biosignal_lab.ai")
    pytest.importorskip("sklearn")
    workflow = Workflow((Node("epochs", "ai_covariance_demo", {"n_subjects": 4, "trials_per_subject": 8}),
                         Node("csp", "csp_evaluate", {"model": "csp_lda", "bootstrap_samples": 100}, {"dataset": Connection("epochs")}),
                         Node("covariance", "csp_evaluate", {"model": "log_euclidean", "bootstrap_samples": 100}, {"dataset": Connection("epochs")})))
    execution = Executor(builtin_registry()).execute(workflow)
    for name in ("csp", "covariance"):
        report = execution.outputs[name]["out"]
        assert report["n_subjects"] == 4 and report["n_samples"] == 32
        assert all(not set(f["train_subjects"]) & set(f["test_subjects"]) for f in report["folds"])
        assert 0 <= report["metrics"]["accuracy"] <= 1


def test_view_state_cannot_change_scientific_schema_or_duplicate_memberships():
    workflow = Workflow((Node("a", "simulate"), Node("b", "simulate")))
    digest = workflow.digest
    positions, groups = clean_view_state(workflow, {"a": {"x": 1, "y": 2}, "b": {"x": float("nan"), "y": 1}},
                                         [{"id": "g1", "name": "First", "nodes": ["a", "b", "missing"]},
                                          {"id": "g2", "name": "Second", "nodes": ["b"]}])
    assert positions == {"a": {"x": 1., "y": 2.}}
    assert groups == [{"id": "g1", "name": "First", "nodes": ["a", "b"]}]
    assert workflow.digest == digest
