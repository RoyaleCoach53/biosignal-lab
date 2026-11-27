"""Subject-disjoint, nested model selection. sklearn is imported only on use."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from importlib.metadata import version
import json
import platform

import numpy as np


@dataclass(frozen=True)
class FeatureDataset:
    X: np.ndarray
    y: np.ndarray
    subjects: np.ndarray
    feature_names: tuple[str, ...] = ()
    provenance: dict = field(default_factory=dict)
    _provenance_json: str = field(init=False, repr=False)

    def __post_init__(self):
        X = np.array(self.X, dtype=np.float64, copy=True)
        raw_y, raw_subjects = np.asarray(self.y), np.asarray(self.subjects)
        if X.ndim != 2 or min(X.shape) < 1 or not np.isfinite(X).all():
            raise ValueError("X must be a nonempty finite samples x features matrix")
        for name, values in [("y", raw_y), ("subjects", raw_subjects)]:
            if values.ndim != 1 or len(values) != len(X):
                raise ValueError(f"{name} must have one value per sample")
            if values.dtype.kind not in "biuUS":
                raise ValueError(f"{name} must contain integer or string identifiers, without nulls")
        y, subjects = raw_y.astype(str), raw_subjects.astype(str)
        if np.any(y == "") or np.any(subjects == "") or len(np.unique(y)) < 2:
            raise ValueError("At least two classes and nonempty subject and class identifiers required")
        names = tuple(self.feature_names or (f"feature_{i}" for i in range(X.shape[1])))
        if len(names) != X.shape[1] or len(set(names)) != len(names) or any(not isinstance(n, str) or not n for n in names):
            raise ValueError("Feature names must be unique nonempty strings matching X")
        for array in (X, y, subjects):
            array.setflags(write=False)
        object.__setattr__(self, "X", X)
        object.__setattr__(self, "y", y)
        object.__setattr__(self, "subjects", subjects)
        object.__setattr__(self, "feature_names", names)
        if not isinstance(self.provenance, dict):
            raise ValueError("Provenance must be a JSON object")
        try:
            encoded = json.dumps(self.provenance, sort_keys=True, allow_nan=False)
        except (ValueError, TypeError) as exc:
            raise ValueError("Provenance must contain strict JSON values") from exc
        if len(encoded.encode()) > 1024 * 1024:
            raise ValueError("Provenance exceeds 1 MiB")
        object.__setattr__(self, "_provenance_json", encoded)
        object.__setattr__(self, "provenance", json.loads(encoded))


def _sklearn():
    try:
        from sklearn import metrics, model_selection, pipeline, preprocessing
    except ImportError as exc:
        raise ImportError("Install biosignal-lab[ai] to use the research ML lab") from exc
    return metrics, model_selection, pipeline, preprocessing


def _classifier(name, seed):
    _sklearn()
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.svm import SVC

    models = {
        "lda": lambda: LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"),
        "qda": lambda: QuadraticDiscriminantAnalysis(reg_param=.1),
        "logistic": lambda: LogisticRegression(max_iter=2000, random_state=seed),
        "svm": lambda: SVC(),
        "random_forest": lambda: RandomForestClassifier(n_estimators=100, random_state=seed, n_jobs=1),
        "knn": lambda: KNeighborsClassifier(n_neighbors=3),
        "gradient_boosting": lambda: GradientBoostingClassifier(random_state=seed),
    }
    if name not in models:
        raise ValueError("Unknown model; choose " + ", ".join(models))
    return models[name]()


def _pipeline(model, seed):
    _, _, pipeline, preprocessing = _sklearn()
    return pipeline.make_pipeline(preprocessing.StandardScaler(), _classifier(model, seed))


def _splits(X, y, groups, cv, n_splits, seed):
    _, selection, _, _ = _sklearn()
    if len(np.unique(groups)) < 2:
        raise ValueError("At least two distinct subjects required for grouped evaluation")
    if cv == "loso":
        splitter = selection.LeaveOneGroupOut()
    elif cv == "group":
        if not isinstance(n_splits, int) or not 2 <= n_splits <= len(np.unique(groups)):
            raise ValueError("n_splits must be between 2 and the number of subjects")
        # StratifiedGroupKFold keeps complete subjects together even with unequal
        # class composition; failure to balance classes is rejected below.
        splitter = selection.StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    else:
        raise ValueError("cv must be loso or group; random window splitting is not supported")
    splits = list(splitter.split(X, y, groups))
    all_classes = set(y)
    for train, test in splits:
        if set(groups[train]) & set(groups[test]):
            raise RuntimeError("Subject leakage detected")
        if set(y[train]) != all_classes:
            raise ValueError("A training fold lacks a class; use a suitable subject/class cohort")
    return splits


def _metrics(y, predicted, classes):
    metrics, _, _, _ = _sklearn()
    precision, recall, f1, support = metrics.precision_recall_fscore_support(
        y, predicted, labels=classes, zero_division=0)
    return {"accuracy": float(metrics.accuracy_score(y, predicted)),
            "balanced_accuracy": float(metrics.balanced_accuracy_score(y, predicted)),
            "macro_f1": float(metrics.f1_score(y, predicted, labels=classes, average="macro", zero_division=0)),
            "confusion_matrix": metrics.confusion_matrix(y, predicted, labels=classes).tolist(),
            "per_class": [{"label": str(label), "precision": float(p), "recall": float(r),
                           "f1": float(f), "support": int(n)}
                          for label, p, r, f, n in zip(classes, precision, recall, f1, support)]}


def evaluate_grouped(dataset: FeatureDataset, model="lda", cv="loso", n_splits=5,
                     seed=42, param_grid=None, inner_splits=3, bootstrap_samples=1000):
    """Return an out-of-fold report; scaler and tuning fit training subjects only.

    Optional ``param_grid`` keys are sklearn pipeline keys, e.g.
    ``logisticregression__C``. Nested grouped inner validation selects parameters
    without using outer test subjects. Confidence intervals resample subjects,
    not correlated windows. No independent clinical performance is implied.
    """
    if not isinstance(dataset, FeatureDataset):
        raise TypeError("dataset must be a FeatureDataset")
    return _evaluate_grouped(dataset, model, cv, n_splits, seed, param_grid,
                             inner_splits, bootstrap_samples)


def _evaluate_grouped(dataset, model, cv, n_splits, seed, param_grid,
                      inner_splits, bootstrap_samples, factory=None):
    if not isinstance(seed, int) or seed < 0 or not isinstance(bootstrap_samples, int) or not 100 <= bootstrap_samples <= 10000:
        raise ValueError("Use a nonnegative integer seed and 100..10000 bootstrap samples")
    if not isinstance(inner_splits, int) or inner_splits < 2:
        raise ValueError("inner_splits must be an integer >=2")
    _, selection, _, _ = _sklearn()
    X, y, groups = dataset.X, dataset.y, dataset.subjects
    classes = np.unique(y)
    predictions = np.empty(y.shape, dtype=y.dtype)
    probabilities = np.empty((len(y), len(classes)))
    has_probabilities = True
    tested = np.zeros(len(y), dtype=int)
    folds = []
    for number, (train, test) in enumerate(_splits(X, y, groups, cv, n_splits, seed)):
        estimator = _pipeline(model, seed) if factory is None else factory(model, seed)
        selected = {}
        if param_grid is not None:
            if not isinstance(param_grid, dict) or not param_grid:
                raise ValueError("param_grid must be a nonempty dictionary")
            inner_groups = groups[train]
            count = min(inner_splits, len(np.unique(inner_groups)))
            inner = _splits(X[train], y[train], inner_groups, "group", count, seed)
            estimator = selection.GridSearchCV(estimator, param_grid, cv=inner,
                                               scoring="balanced_accuracy", n_jobs=1,
                                               error_score="raise", refit=True)
        estimator.fit(X[train], y[train])
        if param_grid is not None:
            selected = estimator.best_params_
        predicted = estimator.predict(X[test])
        predictions[test] = predicted
        if hasattr(estimator, "predict_proba"):
            probabilities[test] = estimator.predict_proba(X[test])
        else:
            has_probabilities = False
        tested[test] += 1
        folds.append({"fold": number, "train_subjects": sorted(set(groups[train])),
                      "test_subjects": sorted(set(groups[test])), "n_train": len(train),
                      "n_test": len(test), "selected_parameters": selected,
                      "metrics": _metrics(y[test], predicted, classes)})
    if not np.all(tested == 1):
        raise RuntimeError("Evaluation must predict every sample exactly once")
    subjects = np.unique(groups)
    per_subject = []
    for subject in subjects:
        mask = groups == subject
        per_subject.append({"subject": str(subject), "n": int(mask.sum()),
                            "metrics": _metrics(y[mask], predictions[mask], classes)})
    subject_accuracy = np.array([item["metrics"]["accuracy"] for item in per_subject])
    rng = np.random.default_rng(seed)
    boot = np.array([rng.choice(subject_accuracy, size=len(subjects), replace=True).mean()
                     for _ in range(bootstrap_samples)])
    digest = sha256()
    # Bind shape, dtype, field identity and sequence boundaries, not just the
    # concatenation of array bytes and length-prefixed identifiers. Otherwise
    # different reshapes and repartitioned metadata can collide structurally.
    envelope = {"fingerprint_schema": "biosignal-ai-input-v2", "shape": list(X.shape),
                "dtype": "<f8", "labels": y.tolist(), "subjects": groups.tolist(),
                "feature_names": list(dataset.feature_names),
                "provenance": json.loads(dataset._provenance_json)}
    encoded = json.dumps(envelope, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    digest.update(len(encoded).to_bytes(8, "big"))
    digest.update(encoded)
    digest.update(X.astype("<f8").tobytes(order="C"))
    discrimination = {"available": False, "reason": "Classifier does not expose class probabilities"}
    if has_probabilities:
        metrics, _, _, _ = _sklearn()
        if len(classes) == 2:
            false_positive, true_positive, thresholds = metrics.roc_curve(y == classes[1], probabilities[:, 1])
            discrimination = {"available": True, "positive_label": str(classes[1]),
                              "auc": float(metrics.roc_auc_score(y == classes[1], probabilities[:, 1])),
                              "false_positive_rate": false_positive.tolist(),
                              "true_positive_rate": true_positive.tolist(),
                              "thresholds": [float(t) if np.isfinite(t) else None for t in thresholds]}
        else:
            discrimination = {"available": True, "macro_ovr_auc": float(metrics.roc_auc_score(
                y, probabilities, labels=classes, multi_class="ovr", average="macro"))}
    return {"schema_version": 1, "task": "subject_disjoint_classification", "model": model,
            "cv": cv, "seed": seed, "n_samples": len(X), "n_features": X.shape[1],
            "n_subjects": len(subjects), "classes": classes.tolist(),
            "features": list(dataset.feature_names), "data_sha256": digest.hexdigest(),
            "data_fingerprint_schema": "biosignal-ai-input-v2",
            "provenance": json.loads(dataset._provenance_json), "roc": discrimination,
            "metrics": _metrics(y, predictions, classes), "folds": folds,
            "per_subject": per_subject, "subject_mean_accuracy": float(subject_accuracy.mean()),
            "subject_bootstrap_accuracy_95ci": np.quantile(boot, [.025, .975]).tolist(),
            "bootstrap_samples": bootstrap_samples,
            "uncertainty_note": "Percentile bootstrap of subject accuracies; small cohorts and overlapping training folds limit inference.",
            "software": {"python": platform.python_version(), "numpy": version("numpy"),
                         "scipy": version("scipy"), "scikit-learn": version("scikit-learn")},
            "limitations": ["Research only; no diagnostic or clinical validation.",
                            "Caller must prevent label-informed preprocessing and overlapping recordings across subjects.",
                            "Feature/schema and dataset hashes support reproducibility, not independent physiological truth."]}


def train_linear(dataset: FeatureDataset, model="lda", seed=42):
    """Fit a deployable linear baseline on all supplied data, without evaluation.

    Use evaluate_grouped first and retain an independent test cohort when needed.
    JSON inference does not require sklearn, and never deserializes Python code.
    """
    if model not in {"lda", "logistic"}:
        raise ValueError("Safe portable export supports lda and logistic only")
    if not isinstance(dataset, FeatureDataset):
        raise TypeError("dataset must be a FeatureDataset")
    fitted = _pipeline(model, seed).fit(dataset.X, dataset.y)
    scaler, classifier = fitted.steps[0][1], fitted.steps[1][1]
    from .portable import LinearModel
    return LinearModel(tuple(classifier.classes_), classifier.coef_, classifier.intercept_,
                       scaler.mean_, scaler.scale_, dataset.feature_names, model)
