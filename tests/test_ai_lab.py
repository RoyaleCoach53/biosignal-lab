"""Analytical features, leakage boundaries, strict model IO and cache integrity."""
from hashlib import sha256
import json

import numpy as np
import pytest

pytest.importorskip("sklearn")

from biosignal_lab.ai import (DatasetManifest, DatasetRecord, FeatureDataset, evaluate_grouped,
                              extract_epoch_features, fetch_record, load_linear_model,
                              save_linear_model, train_linear)
from biosignal_lab.ai.demo import synthetic_feature_dataset
from biosignal_lab.ai.learning import _pipeline


def test_known_tone_features_and_eeg_band_coverage():
    time = np.arange(1000) / 250
    epochs = (10 * np.sin(2 * np.pi * 10 * time))[None, None]
    X, names = extract_epoch_features(epochs, 250)
    assert X[0, names.index("ch1:rms")] == pytest.approx(10 / np.sqrt(2), rel=1e-12)
    assert X[0, names.index("ch1:alpha_power")] == pytest.approx(50, rel=.001)
    assert X[0, names.index("ch1:beta_power")] < .001
    with pytest.raises(ValueError, match="Nyquist"):
        extract_epoch_features(np.ones((1, 1, 200)), 50)
    with pytest.raises(ValueError, match="constant"):
        extract_epoch_features(np.ones((1, 1, 200)), 100, "emg")


def test_emg_frequency_and_integrated_emg_reference():
    time = np.arange(4000) / 2000
    wave = 20 * np.sin(2 * np.pi * 200 * time)
    X, names = extract_epoch_features(wave[None, None], 2000, "emg")
    assert X[0, names.index("ch1:mean_frequency_hz")] == pytest.approx(200, abs=.01)
    assert X[0, names.index("ch1:median_frequency_hz")] == pytest.approx(200)
    assert X[0, names.index("ch1:integrated_emg")] == pytest.approx(np.abs(wave).sum() / 2000)


def test_loso_predicts_once_and_subject_sets_never_overlap():
    data = synthetic_feature_dataset(n_subjects=5, trials_per_subject=6)
    report = evaluate_grouped(data, seed=17, bootstrap_samples=100)
    assert report["metrics"]["balanced_accuracy"] == 1
    assert sum(fold["n_test"] for fold in report["folds"]) == len(data.X)
    assert len(report["folds"]) == 5
    assert sorted(s for fold in report["folds"] for s in fold["test_subjects"]) == sorted(set(data.subjects))
    for fold in report["folds"]:
        assert not set(fold["train_subjects"]) & set(fold["test_subjects"])
    assert report == evaluate_grouped(data, seed=17, bootstrap_samples=100)
    json.dumps(report, allow_nan=False)


def test_nested_grouped_tuning_and_class_incomplete_fold_rejected():
    data = synthetic_feature_dataset(n_subjects=6, trials_per_subject=6)
    result = evaluate_grouped(data, model="logistic", cv="group", n_splits=3,
                              param_grid={"logisticregression__C": [.1, 1.]}, bootstrap_samples=100)
    assert all(fold["selected_parameters"]["logisticregression__C"] in [.1, 1.] for fold in result["folds"])
    only_one_class_per_subject = FeatureDataset([[0], [1], [2], [3]], [0, 0, 1, 1], ["a", "a", "b", "b"])
    with pytest.raises(ValueError, match="lacks a class"):
        evaluate_grouped(only_one_class_per_subject, bootstrap_samples=100)
    with pytest.raises(ValueError, match="random window"):
        evaluate_grouped(data, cv="random", bootstrap_samples=100)


@pytest.mark.parametrize("model", ["lda", "logistic", "qda", "svm", "random_forest", "knn", "gradient_boosting"])
def test_each_registered_classical_baseline_executes_grouped_predictions(model):
    # A controlled separable geometry checks classifier wiring, not a universal
    # accuracy requirement on the oscillation demo with subject-varying gains.
    labels = np.arange(24) % 2
    X = (2 * labels[:, None] - 1) * np.ones((24, 4)) * 3
    X += np.random.default_rng(19).normal(0, .05, size=X.shape)
    data = FeatureDataset(X, labels, np.arange(24) // 8)
    result = evaluate_grouped(data, model=model, bootstrap_samples=100)
    assert result["metrics"]["accuracy"] == 1
    assert sum(sum(row) for row in result["metrics"]["confusion_matrix"]) == len(data.X)
    assert result["roc"]["available"] == (model != "svm")


def test_scaler_is_fit_inside_training_fold(monkeypatch):
    from sklearn.preprocessing import StandardScaler
    data = synthetic_feature_dataset(n_subjects=4, trials_per_subject=6)
    expected = [data.X[data.subjects != subject].mean(axis=0) for subject in np.unique(data.subjects)]
    seen = []
    original = StandardScaler.fit

    def checked_fit(self, X, *args, **kwargs):
        result = original(self, X, *args, **kwargs)
        # LDA's automatic covariance shrinkage also scales each class internally.
        # Inspect only the outer pipeline's complete training-subject matrix.
        if len(X) == 18:
            seen.append(self.mean_.copy())
        return result

    monkeypatch.setattr(StandardScaler, "fit", checked_fit)
    evaluate_grouped(data, bootstrap_samples=100)
    assert len(seen) == 4
    np.testing.assert_allclose(seen, expected)


@pytest.mark.parametrize("model", ["lda", "logistic"])
@pytest.mark.parametrize("classes", [2, 3])
def test_json_model_matches_sklearn_binary_and_multiclass(tmp_path, model, classes):
    rng = np.random.default_rng(2)
    X = rng.normal(size=(60, 4))
    y = np.arange(60) % classes
    data = FeatureDataset(X, y, np.arange(60) // 6)
    expected = _pipeline(model, 42).fit(data.X, data.y)
    portable = train_linear(data, model)
    np.testing.assert_allclose(portable.predict_proba(X), expected.predict_proba(X), atol=1e-12)
    path = tmp_path / "model.json"
    save_linear_model(portable, path)
    loaded = load_linear_model(path)
    np.testing.assert_array_equal(loaded.predict(X), expected.predict(X))
    with pytest.raises(FileExistsError):
        save_linear_model(portable, path)
    payload = json.loads(path.read_text())
    payload["scale"][0] = 0
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="positive"):
        load_linear_model(path)


def test_model_rejects_pickle_duplicate_keys_and_oversized_payload(tmp_path):
    path = tmp_path / "malicious"
    path.write_bytes(b"\x80\x04cos\nsystem\n")
    with pytest.raises((ValueError, UnicodeError)):
        load_linear_model(path)
    path.write_text('{"schema_version":1,"schema_version":1}')
    with pytest.raises(ValueError, match="Duplicate"):
        load_linear_model(path)
    path.write_text(" " * 100)
    with pytest.raises(ValueError, match="byte limit"):
        load_linear_model(path, max_bytes=50)


def test_dataset_rejects_nonfinite_features_and_copies_caller_arrays():
    X = np.array([[1.], [2.]])
    data = FeatureDataset(X, [0, 1], ["a", "b"])
    X[:] = 0
    assert data.X[0, 0] == 1
    with pytest.raises(ValueError):
        data.X[0, 0] = 2
    with pytest.raises(ValueError, match="finite"):
        FeatureDataset([[np.nan], [0]], [0, 1], [0, 1])
    with pytest.raises(ValueError, match="integer or string"):
        FeatureDataset([[0], [1]], [0, 1], [1., np.nan])


def test_dataset_hash_binds_shape_and_metadata_field_boundaries():
    same_bytes = np.arange(48, dtype=float)
    first = FeatureDataset(same_bytes.reshape(4, 12), ["a", "b", "a", "b"],
                            list("abcd"), tuple("efghijklmnop"))
    second = FeatureDataset(same_bytes.reshape(6, 8), ["a", "b", "a", "b", "a", "b"],
                             list("cdefgh"), tuple("ijklmnop"))
    reports = [evaluate_grouped(data, model="knn", bootstrap_samples=100) for data in (first, second)]
    assert reports[0]["data_sha256"] != reports[1]["data_sha256"]
    assert reports[0]["data_fingerprint_schema"] == "biosignal-ai-input-v2"


def _record(path="subject/signal.bin", contents=b"synthetic signal", subject="s1", split="train"):
    return DatasetRecord(path, "https://example.org/signal.bin", sha256(contents).hexdigest(), subject, split)


def test_dataset_manifest_guards_cross_subject_split_and_paths():
    record = _record()
    manifest = DatasetManifest("synthetic", "1", "CC0-1.0", "https://example.org/license", (record,))
    assert len(manifest.digest) == 64
    with pytest.raises(ValueError, match="Subject crosses"):
        DatasetManifest("x", "1", "MIT", "https://example.org/license",
                        (record, _record(path="other.bin", split="test")))
    for path in ["../x", "/x", "a/../x", "C:\\x", "a//x", "a/./x"]:
        with pytest.raises(ValueError, match="relative POSIX"):
            _record(path=path)
    with pytest.raises(ValueError, match="license"):
        DatasetManifest("x", "1", "", "https://example.org/license", (record,))


def test_cache_integrity_opt_in_and_symlink_guard(tmp_path):
    record = _record()
    with pytest.raises(FileNotFoundError, match="opt-in"):
        fetch_record(record, tmp_path)
    with pytest.raises(ValueError, match="license"):
        fetch_record(record, tmp_path, download=True)
    destination = tmp_path / record.path
    destination.parent.mkdir()
    destination.write_bytes(b"synthetic signal")
    assert fetch_record(record, tmp_path) == destination
    destination.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        fetch_record(record, tmp_path, download=True, license_accepted=True)
    assert destination.read_bytes() == b"corrupt"
    destination.unlink()
    destination.symlink_to(tmp_path / "absent")
    with pytest.raises(ValueError, match="symlinks"):
        fetch_record(record, tmp_path)


def test_cache_download_verifies_before_creation_and_enforces_limit(tmp_path, monkeypatch):
    from io import BytesIO
    import biosignal_lab.ai.datasets as cache_module

    def response(body):
        result = BytesIO(body)
        result.url = "https://example.org/signal.bin"
        return result

    monkeypatch.setattr(cache_module, "_open_https", lambda *a, **k: response(b"bad"))
    with pytest.raises(ValueError, match="SHA-256"):
        fetch_record(_record(), tmp_path, download=True, license_accepted=True)
    assert not (tmp_path / _record().path).exists()
    monkeypatch.setattr(cache_module, "_open_https", lambda *a, **k: response(b"synthetic signal"))
    with pytest.raises(ValueError, match="byte limit"):
        fetch_record(_record(), tmp_path, download=True, license_accepted=True, max_bytes=4)
    destination = fetch_record(_record(), tmp_path, download=True, license_accepted=True)
    assert destination.read_bytes() == b"synthetic signal"


def test_cache_rejects_root_symlink_and_https_downgrade_before_following(tmp_path, monkeypatch):
    from urllib.request import HTTPRedirectHandler, Request
    from biosignal_lab.ai.datasets import _HTTPSOnlyRedirect
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="root.*symlinks"):
        fetch_record(_record(), alias)
    with pytest.raises(ValueError, match="root.*symlinks"):
        fetch_record(_record(), alias / "subdirectory")
    followed = []

    def redirect(self, request, response, code, message, headers, newurl):
        followed.append(newurl)
        return Request(newurl)

    monkeypatch.setattr(HTTPRedirectHandler, "redirect_request", redirect)
    handler = _HTTPSOnlyRedirect()
    request = Request("https://example.org/data")
    with pytest.raises(ValueError, match="credential-free HTTPS"):
        handler.redirect_request(request, None, 302, "Found", {}, "http://example.org/data")
    assert followed == []
    handler.redirect_request(request, None, 302, "Found", {}, "https://example.org/secure")
    assert followed == ["https://example.org/secure"]


def test_ai_dashboard_executes_real_grouped_evaluation():
    pytest.importorskip("streamlit")
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "ai_app.py"), default_timeout=60).run()
    assert not app.exception
    assert not app.metric
    next(button for button in app.button if button.label == "Run grouped evaluation").click().run()
    assert not app.exception
    assert len(app.metric) == 4
    assert app.session_state["ai_report"]["n_subjects"] == 8
    assert app.session_state["ai_report"]["metrics"]["confusion_matrix"] == [[64, 0], [0, 64]]
