"""Analytical spatial covariance controls and grouped fit-boundary tests."""
import numpy as np
import pytest

pytest.importorskip("sklearn")

from biosignal_lab.ai import (CSPTransformer, EpochDataset, LogEuclideanClassifier,
                              evaluate_epochs)


def _spatial_data(seed=3):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(48, 4, 400))
    y = np.arange(48) % 2
    X[y == 0, 0] *= 3
    X[y == 1, 1] *= 3
    return EpochDataset(X, y, np.arange(48) // 8, 200, "uv", reference="synthetic independent channels")


def test_csp_matches_analytical_diagonal_covariance_eigenvalues():
    time = np.arange(1000) / 1000
    first = np.array([3 * np.sin(2 * np.pi * 10 * time), np.cos(2 * np.pi * 10 * time)])
    second = np.array([np.sin(2 * np.pi * 10 * time), 3 * np.cos(2 * np.pi * 10 * time)])
    X = np.array([first, second, first, second])
    csp = CSPTransformer(2, regularization=.01).fit(X, [0, 1, 0, 1])
    # Trace-normalized class covariance .9/.1, shrunk .01 toward .5/.5.
    np.testing.assert_allclose(csp.eigenvalues_, [.896, .104], atol=1e-12)
    features = csp.transform(X)
    assert features[0, 0] > features[0, 1]
    assert features[1, 1] > features[1, 0]
    np.testing.assert_allclose(np.exp(features).sum(axis=1), 1)
    with pytest.raises(ValueError, match="2..number"):
        CSPTransformer(1).fit(X, [0, 1, 0, 1])
    with pytest.raises(ValueError, match="exactly two"):
        CSPTransformer(2).fit(X, [0, 1, 2, 2])


def test_covariance_distance_invariant_to_shared_orthogonal_rotation():
    data = _spatial_data()
    rng = np.random.default_rng(8)
    rotation = np.linalg.qr(rng.normal(size=(4, 4)))[0]
    rotated = np.einsum("kc,nct->nkt", rotation, data.X)
    original = LogEuclideanClassifier().fit(data.X[:32], data.y[:32])
    changed_basis = LogEuclideanClassifier().fit(rotated[:32], data.y[:32])
    np.testing.assert_array_equal(original.predict(data.X[32:]), changed_basis.predict(rotated[32:]))
    assert np.mean(original.predict(data.X[32:]) == data.y[32:]) == 1


@pytest.mark.parametrize("model", ["csp_lda", "log_euclidean"])
def test_spatial_loso_and_nested_group_tuning(model):
    data = _spatial_data()
    report = evaluate_epochs(data, model=model, n_components=2, bootstrap_samples=100)
    assert report["metrics"]["balanced_accuracy"] == 1
    assert report["n_channels"] == 4 and report["n_samples_per_epoch"] == 400
    assert report["provenance"]["amplitude_unit"] == "uv"
    params = {"csptransformer__n_components": [2, 4]} if model == "csp_lda" else {"regularization": [.01, .1]}
    tuned = evaluate_epochs(data, model=model, n_components=2, cv="group", n_splits=3,
                             param_grid=params, bootstrap_samples=100)
    assert all(fold["selected_parameters"] for fold in tuned["folds"])
    assert tuned["metrics"]["accuracy"] == 1


def test_csp_fit_never_sees_outer_test_epochs(monkeypatch):
    data = _spatial_data()
    original = CSPTransformer.fit
    seen = []

    def checked(self, X, y):
        seen.append(X.copy())
        return original(self, X, y)

    monkeypatch.setattr(CSPTransformer, "fit", checked)
    evaluate_epochs(data, n_components=2, bootstrap_samples=100)
    assert len(seen) == 6
    for X, subject in zip(seen, np.unique(data.subjects)):
        np.testing.assert_array_equal(X, data.X[data.subjects != subject])


def test_spatial_validation_rank_deficiency_and_zero_energy():
    data = _spatial_data()
    dependent = np.repeat(data.X[:, :1], 2, axis=1)
    result = CSPTransformer(2).fit(dependent, data.y).transform(dependent)
    assert np.isfinite(result).all()
    with pytest.raises(ValueError, match="Zero-energy"):
        CSPTransformer(2).fit(np.zeros((4, 2, 100)), [0, 1, 0, 1])
    with pytest.raises(ValueError, match="sampling"):
        EpochDataset(data.X, data.y, data.subjects, 0, "uv")
    with pytest.raises(ValueError, match="before prediction"):
        LogEuclideanClassifier().predict(data.X)


def test_ai_cli_creates_new_experiment_and_preserves_old(tmp_path, capsys):
    from biosignal_lab.ai.cli import main
    output = tmp_path / "experiment"
    assert main(["demo", "--output", str(output), "--subjects", "4"]) == 0
    assert (output / "evaluation.json").exists()
    model_bytes = (output / "model.json").read_bytes()
    with pytest.raises(SystemExit) as error:
        main(["demo", "--output", str(output)])
    assert error.value.code == 1
    assert (output / "model.json").read_bytes() == model_bytes
    assert "No physiological task validated" in capsys.readouterr().out
