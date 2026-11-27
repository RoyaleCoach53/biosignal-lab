"""Strict bounded JSON for affine LDA/logistic inference; never pickle models."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path

import numpy as np
from scipy.special import expit, softmax


@dataclass(frozen=True)
class LinearModel:
    classes: tuple[str, ...]
    coefficients: np.ndarray
    intercept: np.ndarray
    mean: np.ndarray
    scale: np.ndarray
    feature_names: tuple[str, ...]
    algorithm: str

    def __post_init__(self):
        if not isinstance(self.classes, (tuple, list)) or not isinstance(self.feature_names, (tuple, list)):
            raise ValueError("Classes and feature names must be explicit sequences of strings")
        classes, names = tuple(self.classes), tuple(self.feature_names)
        if not isinstance(self.algorithm, str) or self.algorithm not in {"lda", "logistic"}:
            raise ValueError("Unsupported portable algorithm")
        if not 2 <= len(classes) <= 1000 or len(set(classes)) != len(classes):
            raise ValueError("Expected 2..1000 unique classes")
        if not 1 <= len(names) <= 100000 or len(set(names)) != len(names):
            raise ValueError("Expected unique feature names")
        if any(not isinstance(s, str) or not s or len(s) > 1024 for s in (*classes, *names)):
            raise ValueError("Class and feature names must be bounded nonempty strings")
        expected = 1 if len(classes) == 2 else len(classes)
        shapes = {"coefficients": (expected, len(names)), "intercept": (expected,),
                  "mean": (len(names),), "scale": (len(names),)}
        for field, shape in shapes.items():
            if np.asarray(getattr(self, field)).dtype.kind not in "iuf":
                raise ValueError(f"{field} must contain real numeric values")
            value = np.array(getattr(self, field), dtype=float, copy=True)
            if value.shape != shape or not np.isfinite(value).all():
                raise ValueError(f"Invalid {field} shape or nonfinite data")
            if field == "scale" and np.any(value <= 0):
                raise ValueError("All scales must be positive")
            value.setflags(write=False)
            object.__setattr__(self, field, value)
        object.__setattr__(self, "classes", classes)
        object.__setattr__(self, "feature_names", names)

    def predict_proba(self, X):
        X = np.asarray(X, dtype=float)
        if X.ndim != 2 or X.shape[1] != len(self.feature_names) or not np.isfinite(X).all():
            raise ValueError("Expected finite samples x model features")
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            try:
                decision = ((X - self.mean) / self.scale) @ self.coefficients.T + self.intercept
            except FloatingPointError as exc:
                raise ValueError("Model arithmetic overflow") from exc
        if len(self.classes) == 2:
            positive = expit(decision[:, 0])
            return np.column_stack((1 - positive, positive))
        return softmax(decision, axis=1)

    def predict(self, X):
        return np.array(self.classes)[self.predict_proba(X).argmax(axis=1)]

    def to_dict(self):
        return {"schema_version": 1, "format": "biosignal-linear-json",
                "algorithm": self.algorithm, "classes": list(self.classes),
                "feature_names": list(self.feature_names), "coefficients": self.coefficients.tolist(),
                "intercept": self.intercept.tolist(), "mean": self.mean.tolist(),
                "scale": self.scale.tolist(),
                "scope": "Affine research classifier; no execution of model code or clinical validation."}


def save_linear_model(model: LinearModel, path):
    """Create a new JSON file. Existing model files are never overwritten."""
    if not isinstance(model, LinearModel):
        raise TypeError("Expected a validated LinearModel")
    content = json.dumps(model.to_dict(), indent=2, allow_nan=False) + "\n"
    with Path(path).open("x", encoding="utf-8") as output:
        output.write(content)


def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON keys are not accepted")
        value[key] = item
    return value


def _real_json_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(float(value))
    except (ValueError, TypeError, OverflowError):
        return False


def load_linear_model(path, max_bytes=8 * 1024 * 1024):
    """Load bounded, schema-checked JSON. No pickle, joblib or import strings."""
    if not isinstance(max_bytes, int) or not 1 <= max_bytes <= 32 * 1024 * 1024:
        raise ValueError("Model read limit must be 1..32 MiB")
    with Path(path).open("rb") as stream:
        raw = stream.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("Model exceeds configured byte limit")
    data = json.loads(raw, object_pairs_hook=_unique_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
    required = {"schema_version", "format", "algorithm", "classes", "feature_names",
                "coefficients", "intercept", "mean", "scale", "scope"}
    if not isinstance(data, dict) or set(data) != required or type(data["schema_version"]) is not int or data["schema_version"] != 1 or data["format"] != "biosignal-linear-json":
        raise ValueError("Unsupported model schema")
    for field in ("classes", "feature_names"):
        if not isinstance(data[field], list) or any(not isinstance(item, str) for item in data[field]):
            raise ValueError(f"{field} must be a JSON array of strings")
    if not isinstance(data["algorithm"], str) or not isinstance(data["scope"], str):
        raise ValueError("Model algorithm and scope must be JSON strings")
    for field in ("coefficients", "intercept", "mean", "scale"):
        values = data[field]
        if not isinstance(values, list):
            raise ValueError(f"{field} must be a numeric JSON array")
        if field == "coefficients":
            if any(not isinstance(row, list) for row in values):
                raise ValueError("Coefficients must be a nested numeric JSON array")
            values = [item for row in values for item in row]
        if any(not _real_json_number(item) for item in values):
            raise ValueError(f"{field} requires finite JSON numbers, excluding booleans")
    return LinearModel(data["classes"], data["coefficients"], data["intercept"],
                       data["mean"], data["scale"], data["feature_names"], data["algorithm"])
