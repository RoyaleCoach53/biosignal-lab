"""Actual CPU training, held-out partition boundaries and safe weight parsing."""
import json

import numpy as np
import pytest

pytest.importorskip("sklearn")
torch = pytest.importorskip("torch")

from biosignal_lab.ai import (EpochDataset, load_temporal_model, save_temporal_model,
                              train_temporal)
from biosignal_lab.ai.demo import synthetic_epoch_dataset


def _metadata(data):
    return {"sfreq": data.sfreq, "unit": data.unit, "channels": data.channels,
            "reference": data.reference}


def test_temporal_training_is_deterministic_and_training_only_normalized(tmp_path):
    data = synthetic_epoch_dataset(seed=7, n_subjects=4, trials_per_subject=8)
    old_threads = torch.get_num_threads()
    model, report = train_temporal(data, seed=9, max_epochs=8, patience=3, batch_size=8)
    second, repeated = train_temporal(data, seed=9, max_epochs=8, patience=3, batch_size=8)
    assert torch.get_num_threads() == old_threads
    assert not set(report["train_subjects"]) & set(report["validation_subjects"])
    assert not set(report["train_subjects"]) & set(report["test_subjects"])
    assert not set(report["validation_subjects"]) & set(report["test_subjects"])
    assert report["n_test"] == 8 and report["n_train"] == 16
    training = np.isin(data.subjects, report["train_subjects"])
    np.testing.assert_allclose(report["normalization"]["mean"], data.X[training].mean(axis=(0, 2)))
    assert report["history"] == repeated["history"]
    assert report["history"][-1]["train_loss"] < report["history"][0]["train_loss"]
    probability = model.predict_proba(data.X, **_metadata(data))
    np.testing.assert_allclose(probability.sum(axis=1), 1, atol=1e-6)
    np.testing.assert_array_equal(probability, second.predict_proba(data.X, **_metadata(data)))
    path = tmp_path / "temporal.json"
    save_temporal_model(model, path)
    loaded = load_temporal_model(path)
    np.testing.assert_array_equal(probability, loaded.predict_proba(data.X, **_metadata(data)))
    with pytest.raises(FileExistsError):
        save_temporal_model(model, path)
    metadata = _metadata(data)
    metadata["unit"] = "incorrect"
    with pytest.raises(ValueError, match="must match training"):
        loaded.predict_proba(data.X, **metadata)


def test_test_label_changes_cannot_change_fitted_weights_or_checkpoint():
    data = synthetic_epoch_dataset(seed=7, n_subjects=4, trials_per_subject=8)
    changed_y = data.y.copy()
    test = data.subjects == sorted(set(data.subjects))[-1]
    changed_y[test] = changed_y[test][::-1]
    changed = EpochDataset(data.X, changed_y, data.subjects, data.sfreq, data.unit,
                            data.channels, data.reference, data.provenance)
    model, report = train_temporal(data, max_epochs=4, patience=2)
    other, changed_report = train_temporal(changed, max_epochs=4, patience=2)
    assert report["history"] == changed_report["history"]
    assert report["best_epoch"] == changed_report["best_epoch"]
    for key, value in model.network.state_dict().items():
        assert torch.equal(value, other.network.state_dict()[key])


def test_temporal_partition_and_resource_rejection_precedes_training():
    data = synthetic_epoch_dataset(n_subjects=4, trials_per_subject=4)
    with pytest.raises(ValueError, match="disjoint"):
        train_temporal(data, train_subjects=["synthetic_000", "synthetic_001"],
                        validation_subjects=["synthetic_001"], test_subjects=["synthetic_003"])
    with pytest.raises(ValueError, match="memory budget"):
        train_temporal(data, memory_budget_bytes=1)
    with pytest.raises(ValueError, match="Supply all"):
        train_temporal(data, train_subjects=["synthetic_000"])


def test_temporal_checkpoint_rejects_unknown_tensor_names_and_numeric_coercion(tmp_path):
    data = synthetic_epoch_dataset(n_subjects=3, trials_per_subject=4)
    model, _ = train_temporal(data, max_epochs=1)
    path = tmp_path / "weights.json"
    save_temporal_model(model, path)
    original = json.loads(path.read_text())
    malformed = dict(original, weights={"__reduce__": "os.system"})
    path.write_text(json.dumps(malformed))
    with pytest.raises(ValueError, match="tensor names"):
        load_temporal_model(path)
    malformed = dict(original, mean=["0"] * len(data.channels))
    path.write_text(json.dumps(malformed))
    with pytest.raises(ValueError, match="finite JSON numbers"):
        load_temporal_model(path)
    malformed = dict(original, sfreq=10**400)
    path.write_text(json.dumps(malformed))
    with pytest.raises(ValueError, match="finite JSON numbers"):
        load_temporal_model(path)
    path.write_bytes(b"\x80\x04cos\nsystem\n")
    with pytest.raises((ValueError, UnicodeError)):
        load_temporal_model(path)


@pytest.mark.parametrize("representation,architecture", [("Temporal Conv1D", "temporal_conv1d_v1"),
                                                        ("EEGNet", "eegnet_v1")])
def test_ai_dashboard_executes_actual_temporal_training(representation, architecture):
    pytest.importorskip("streamlit")
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "ai_app.py"), default_timeout=60).run()
    next(select for select in app.selectbox if select.label == "Representation").set_value(representation).run()
    next(slider for slider in app.slider if slider.label == "Maximum training epochs").set_value(2).run()
    next(slider for slider in app.slider if slider.label == "Simulated subjects").set_value(4).run()
    next(button for button in app.button if button.label == "Run grouped evaluation").click().run()
    assert not app.exception
    report = app.session_state["ai_report"]
    assert report["model"] == architecture
    assert report["epochs_executed"] == 2
    assert report["n_train"] == 32 and report["n_validation"] == 16 and report["n_test"] == 16
    assert app.session_state["ai_neural_model"]["format"] == "biosignal-temporal-json"


def test_eegnet_actual_training_spatial_constraint_and_safe_checkpoint(tmp_path):
    data = synthetic_epoch_dataset(n_subjects=4, trials_per_subject=8)
    model, report = train_temporal(data, architecture="eegnet_v1", max_epochs=3,
                                   patience=2, batch_size=4)
    assert report["architecture"] == "eegnet_v1" and report["epochs_executed"] >= 1
    spatial = model.network[4].weight.detach()
    dense = model.network[-1].weight.detach()
    assert torch.linalg.vector_norm(spatial, dim=(1, 2, 3)).max() <= 1.000001
    assert torch.linalg.vector_norm(dense, dim=1).max() <= .250001
    probability = model.predict_proba(data.X, **_metadata(data))
    assert probability.shape == (32, 2)
    np.testing.assert_allclose(probability.sum(axis=1), 1, atol=1e-6)
    path = tmp_path / "eegnet.json"
    save_temporal_model(model, path)
    restored = load_temporal_model(path)
    np.testing.assert_array_equal(probability, restored.predict_proba(data.X, **_metadata(data)))
    with pytest.raises(ValueError, match="epoch length"):
        restored.predict_proba(data.X[:, :, :-1], **_metadata(data))
    payload = json.loads(path.read_text())
    payload["weights"]["3.num_batches_tracked"] = 1.5
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="Integer tensor counters"):
        load_temporal_model(path)


def test_neural_validation_and_test_forward_batches_respect_limit(monkeypatch):
    import biosignal_lab.ai.neural as module
    data = synthetic_epoch_dataset(n_subjects=4, trials_per_subject=8)
    observed = []
    original = module._network

    def checked(*args, **kwargs):
        model = original(*args, **kwargs)
        model.register_forward_pre_hook(lambda module, inputs: observed.append(len(inputs[0])))
        return model

    monkeypatch.setattr(module, "_network", checked)
    train_temporal(data, max_epochs=1, batch_size=3)
    assert max(observed) <= 3


def test_neural_cli_generates_actual_safe_weights_and_holdout_report(tmp_path):
    from biosignal_lab.ai.cli import main
    output = tmp_path / "neural"
    assert main(["neural-demo", "--output", str(output), "--subjects", "3",
                 "--max-epochs", "1", "--architecture", "eegnet_v1"]) == 0
    report = json.loads((output / "evaluation.json").read_text())
    assert report["architecture"] == "eegnet_v1" and report["epochs_executed"] == 1
    assert load_temporal_model(output / "model.json").architecture == "eegnet_v1"
