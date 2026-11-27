"""Training-only spatial baselines for epoched research data.

CSP is binary log-variance classification. The covariance baseline uses a
log-Euclidean metric on regularized SPD matrices, not the affine-invariant metric.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json

import numpy as np
from scipy.linalg import eigh

from .learning import FeatureDataset, _evaluate_grouped, _sklearn


def _epochs(data):
    if np.iscomplexobj(data):
        raise ValueError("Covariance epochs require real amplitudes")
    data = np.asarray(data, dtype=float)
    if data.ndim != 3 or data.shape[0] < 1 or data.shape[1] < 1 or data.shape[2] < 16:
        raise ValueError("Expected nonempty epochs x channels x samples with >=16 samples")
    if not np.isfinite(data).all():
        raise ValueError("Covariance epochs must contain only finite values")
    return data


def _covariances(data, regularization=.01, normalize_trace=False):
    data = _epochs(data)
    if not np.isfinite(regularization) or not 0 < regularization <= 1:
        raise ValueError("Covariance shrinkage must be in (0,1]")
    centered = data - data.mean(axis=-1, keepdims=True)
    with np.errstate(over="raise", invalid="raise"):
        try:
            covariance = centered @ centered.transpose(0, 2, 1) / (data.shape[-1] - 1)
        except FloatingPointError as exc:
            raise ValueError("Covariance overflow; explicitly rescale the input") from exc
    trace = np.trace(covariance, axis1=1, axis2=2)
    if np.any(trace <= np.finfo(float).tiny) or not np.isfinite(trace).all():
        raise ValueError("Zero-energy or unrepresentable epochs have undefined covariance features")
    if normalize_trace:
        covariance = covariance / trace[:, None, None]
        trace = np.ones(len(covariance))
    channels = data.shape[1]
    return ((1 - regularization) * covariance
            + regularization * (trace / channels)[:, None, None] * np.eye(channels))


@dataclass(frozen=True)
class EpochDataset:
    """Epochs and labels with explicit frequency/units/reference provenance."""
    X: np.ndarray
    y: np.ndarray
    subjects: np.ndarray
    sfreq: float
    unit: str
    channels: tuple[str, ...] = ()
    reference: str = "unspecified"
    provenance: dict = field(default_factory=dict)

    def __post_init__(self):
        epochs = _epochs(self.X).copy()
        if not np.isfinite(self.sfreq) or self.sfreq <= 0 or not isinstance(self.unit, str) or not self.unit:
            raise ValueError("Require a finite positive sampling rate and explicit amplitude unit")
        names = tuple(self.channels or (f"ch{i+1}" for i in range(epochs.shape[1])))
        if len(names) != epochs.shape[1] or len(set(names)) != len(names):
            raise ValueError("Channel names must uniquely match the channel axis")
        if any(not isinstance(n, str) or not n for n in names) or not isinstance(self.reference, str) or not self.reference:
            raise ValueError("Channel names and reference must be nonempty strings")
        if not isinstance(self.provenance, dict):
            raise ValueError("Provenance must be a JSON object")
        provenance = {**self.provenance, "sampling_frequency_hz": self.sfreq, "amplitude_unit": self.unit,
                      "reference": self.reference, "input_shape": list(epochs.shape), "channels": list(names)}
        # Reuse identifier/schema validation without flattening or copying epoch data again.
        validated = FeatureDataset(np.zeros((len(epochs), 1)), self.y, self.subjects,
                                   ("validation_only",), provenance)
        epochs.setflags(write=False)
        object.__setattr__(self, "X", epochs)
        object.__setattr__(self, "y", validated.y)
        object.__setattr__(self, "subjects", validated.subjects)
        object.__setattr__(self, "channels", names)
        object.__setattr__(self, "feature_names", names)
        object.__setattr__(self, "_provenance_json", validated._provenance_json)
        object.__setattr__(self, "provenance", json.loads(validated._provenance_json))


class CSPTransformer:
    """Binary CSP, alternating largest/smallest generalized eigenvalue filters.

    A small relative covariance shrinkage makes rank deficiency explicit and
    stable. Fit uses training labels only. Features are log normalized projected
    variance; filters are spatial mixtures of scalp potentials, not neural sources.
    """
    def __init__(self, n_components=4, regularization=.01):
        self.n_components = n_components
        self.regularization = regularization

    def get_params(self, deep=True):
        return {"n_components": self.n_components, "regularization": self.regularization}

    def __sklearn_tags__(self):
        # Keep sklearn optional when importing safe JSON inference. Tags are
        # requested only by sklearn meta-estimators in versions >=1.6.
        from sklearn.base import BaseEstimator, TransformerMixin

        class TagsProvider(TransformerMixin, BaseEstimator):
            pass

        tags = TagsProvider().__sklearn_tags__()
        tags.input_tags.two_d_array = False
        tags.input_tags.three_d_array = True
        return tags

    def set_params(self, **params):
        for key, value in params.items():
            if key not in self.get_params():
                raise ValueError(f"Unknown CSP parameter {key}")
            setattr(self, key, value)
        return self

    def fit(self, X, y):
        X, y = _epochs(X), np.asarray(y)
        if y.ndim != 1 or len(y) != len(X) or len(np.unique(y)) != 2:
            raise ValueError("CSP requires exactly two training classes")
        if not isinstance(self.n_components, int) or not 2 <= self.n_components <= X.shape[1]:
            raise ValueError("CSP components must be 2..number of channels")
        covariance = _covariances(X, self.regularization, normalize_trace=True)
        self.classes_ = np.unique(y)
        first, second = [covariance[y == label].mean(axis=0) for label in self.classes_]
        eigenvalues, eigenvectors = eigh(first, first + second)
        order = []
        low, high = 0, X.shape[1] - 1
        while low <= high:
            order.append(high)
            if low < high:
                order.append(low)
            low, high = low + 1, high - 1
        selected = order[:self.n_components]
        self.filters_ = eigenvectors[:, selected].T
        self.eigenvalues_ = eigenvalues[selected]
        self.n_features_in_ = X.shape[1]
        return self

    def transform(self, X):
        X = _epochs(X)
        if not hasattr(self, "filters_"):
            raise ValueError("CSP must be fitted on training epochs before transform")
        if X.shape[1] != self.n_features_in_:
            raise ValueError("CSP channel count differs from training")
        projected = np.einsum("kc,nct->nkt", self.filters_, X - X.mean(axis=-1, keepdims=True))
        variance = np.mean(projected ** 2, axis=-1)
        total = variance.sum(axis=1, keepdims=True)
        if np.any(total <= np.finfo(float).tiny) or not np.isfinite(total).all():
            raise ValueError("Projected epoch has undefined variance")
        return np.log(np.maximum(variance / total, np.finfo(float).tiny))

    def fit_transform(self, X, y=None, **fit_params):
        return self.fit(X, y).transform(X)


class LogEuclideanClassifier:
    """Nearest class mean in log-Euclidean SPD covariance geometry.

    This baseline has no learned probability calibration. Regularization shrinks
    each epoch covariance toward its scaled identity before the matrix logarithm.
    """
    _estimator_type = "classifier"

    def __init__(self, regularization=.01):
        self.regularization = regularization

    def get_params(self, deep=True):
        return {"regularization": self.regularization}

    def __sklearn_tags__(self):
        from sklearn.base import BaseEstimator, ClassifierMixin

        class TagsProvider(ClassifierMixin, BaseEstimator):
            pass

        tags = TagsProvider().__sklearn_tags__()
        tags.input_tags.two_d_array = False
        tags.input_tags.three_d_array = True
        return tags

    def set_params(self, **params):
        for key, value in params.items():
            if key != "regularization":
                raise ValueError(f"Unknown covariance parameter {key}")
            setattr(self, key, value)
        return self

    def _logs(self, X):
        covariance = _covariances(X, self.regularization)
        values, vectors = np.linalg.eigh(covariance)
        if np.any(values <= 0):
            raise ValueError("Covariances must be strictly positive definite")
        return (vectors * np.log(values)[:, None, :]) @ vectors.transpose(0, 2, 1)

    def fit(self, X, y):
        X, y = _epochs(X), np.asarray(y)
        if y.ndim != 1 or len(y) != len(X) or len(np.unique(y)) < 2:
            raise ValueError("At least two classes with one label per epoch required")
        logs = self._logs(X)
        self.classes_ = np.unique(y)
        self.means_ = np.array([logs[y == label].mean(axis=0) for label in self.classes_])
        self.n_features_in_ = X.shape[1]
        return self

    def predict(self, X):
        X = _epochs(X)
        if not hasattr(self, "means_"):
            raise ValueError("Covariance classifier must be fitted before prediction")
        if X.shape[1] != self.n_features_in_:
            raise ValueError("Covariance channel count differs from training")
        logs = self._logs(X)
        distances = np.sum((logs[:, None] - self.means_[None]) ** 2, axis=(2, 3))
        return self.classes_[distances.argmin(axis=1)]


def evaluate_epochs(dataset: EpochDataset, model="csp_lda", cv="loso", n_splits=5,
                    seed=42, n_components=4, regularization=.01, param_grid=None,
                    inner_splits=3, bootstrap_samples=1000):
    """Evaluate CSP/LDA or log-Euclidean covariance with complete held-out subjects.

    Spatial fitting and class means occur inside each fold, including nested
    tuning. The caller must choose a valid prior reference, montage and epochs.
    """
    if not isinstance(dataset, EpochDataset):
        raise TypeError("dataset must be an EpochDataset")
    if model not in {"csp_lda", "log_euclidean"}:
        raise ValueError("Epoch model must be csp_lda or log_euclidean")

    def factory(name, ignored_seed):
        _, _, pipeline, preprocessing = _sklearn()
        if name == "log_euclidean":
            return LogEuclideanClassifier(regularization)
        from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
        return pipeline.make_pipeline(CSPTransformer(n_components, regularization),
                                      preprocessing.StandardScaler(),
                                      LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"))

    report = _evaluate_grouped(dataset, model, cv, n_splits, seed, param_grid,
                               inner_splits, bootstrap_samples, factory=factory)
    report["task"] = "subject_disjoint_epoch_classification"
    report["n_channels"] = dataset.X.shape[1]
    report["n_samples_per_epoch"] = dataset.X.shape[2]
    used_components = [fold["selected_parameters"].get("csptransformer__n_components", n_components)
                       for fold in report["folds"]]
    count = used_components[0] if len(set(used_components)) == 1 else None
    report["n_features"] = count if model == "csp_lda" else dataset.X.shape[1] * (dataset.X.shape[1] + 1) // 2
    if model == "csp_lda":
        report["features"] = [f"csp_log_variance_{i+1}" for i in range(count)] if count is not None else []
    else:
        report["features"] = ["symmetric_log_covariance"]
    for fold, components in zip(report["folds"], used_components):
        fold["executed_parameters"] = {"n_components": components if model == "csp_lda" else None,
                                        "covariance_shrinkage": fold["selected_parameters"].get(
                                            "csptransformer__regularization" if model == "csp_lda" else "regularization", regularization)}
    report["base_parameters"] = {"n_components": n_components if model == "csp_lda" else None,
                             "covariance_shrinkage": regularization,
                             "geometry": "log_euclidean" if model == "log_euclidean" else "generalized_eigenvectors"}
    report["features_note"] = "Spatial filters are fitted separately in each fold; component indices do not denote shared maps. n_features is null when tuned dimensions vary."
    report["limitations"].append("Spatial filters are mixtures of scalp channels, not inferred neural sources.")
    return report
