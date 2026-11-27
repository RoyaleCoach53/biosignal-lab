"""Optional lightweight temporal Conv1D research baseline, CPU and explicit splits.

No pretrained weights, physiological performance claims, or executable checkpoints.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from .covariance import EpochDataset, _epochs
from .learning import _metrics
from .portable import _real_json_number, _unique_pairs


def _torch():
    try:
        import torch
    except ImportError as exc:
        raise ImportError("Install the neural extra with a suitable official CPU/GPU PyTorch wheel") from exc
    return torch


def _network(channels, classes):
    torch = _torch()
    if not isinstance(channels, int) or not 1 <= channels <= 128 or not isinstance(classes, int) or not 2 <= classes <= 256:
        raise ValueError("Temporal Conv1D supports 1..128 channels and 2..256 classes")
    return torch.nn.Sequential(
        torch.nn.Conv1d(channels, 16, kernel_size=15, padding=7), torch.nn.ELU(),
        torch.nn.AvgPool1d(4), torch.nn.Conv1d(16, 32, kernel_size=9, padding=4),
        torch.nn.ELU(), torch.nn.AdaptiveAvgPool1d(1), torch.nn.Flatten(),
        torch.nn.Linear(32, classes),
    )


@dataclass
class TemporalModel:
    network: object
    classes: tuple[str, ...]
    channels: tuple[str, ...]
    sfreq: float
    unit: str
    reference: str
    mean: np.ndarray
    scale: np.ndarray

    def __post_init__(self):
        if not isinstance(self.classes, (tuple, list)) or not isinstance(self.channels, (tuple, list)):
            raise ValueError("Classes/channels require explicit sequences")
        self.classes, self.channels = tuple(self.classes), tuple(self.channels)
        if not 2 <= len(self.classes) <= 256 or len(set(self.classes)) != len(self.classes):
            raise ValueError("Require 2..256 unique classes")
        if not 1 <= len(self.channels) <= 128 or len(set(self.channels)) != len(self.channels):
            raise ValueError("Require 1..128 unique channels")
        if any(not isinstance(s, str) or not s or len(s) > 1024 for s in (*self.classes, *self.channels, self.unit, self.reference)):
            raise ValueError("Require explicit bounded class/channel/unit/reference strings")
        if not np.isfinite(self.sfreq) or self.sfreq <= 0:
            raise ValueError("Require positive sampling frequency")
        self.mean, self.scale = np.array(self.mean, dtype=float), np.array(self.scale, dtype=float)
        if self.mean.shape != (len(self.channels),) or self.scale.shape != self.mean.shape or not np.isfinite(self.mean).all() or not np.isfinite(self.scale).all() or np.any(self.scale <= 0):
            raise ValueError("Invalid training-only channel normalization")
        self.network.cpu().eval()

    def predict_proba(self, epochs, *, sfreq, unit, channels, reference, batch_size=64):
        if sfreq != self.sfreq or unit != self.unit or tuple(channels) != self.channels or reference != self.reference:
            raise ValueError("Inference sampling frequency, unit, channel order and reference must match training")
        X = _epochs(epochs)
        if X.shape[1] != len(self.channels) or not isinstance(batch_size, int) or not 1 <= batch_size <= 1024:
            raise ValueError("Invalid inference channels or batch size")
        torch = _torch()
        predictions = []
        self.network.eval()
        with torch.no_grad():
            for start in range(0, len(X), batch_size):
                normalized = _normalize(X[start:start + batch_size], self.mean, self.scale)
                result = torch.softmax(self.network(torch.from_numpy(normalized)), dim=1)
                if not torch.isfinite(result).all():
                    raise ValueError("Nonfinite neural model output")
                predictions.append(result.numpy())
        return np.concatenate(predictions)

    def predict(self, epochs, **metadata):
        return np.array(self.classes)[self.predict_proba(epochs, **metadata).argmax(axis=1)]

    def to_dict(self):
        return {"schema_version": 1, "format": "biosignal-temporal-json", "architecture": "temporal_conv1d_v1",
                "classes": list(self.classes), "channels": list(self.channels), "sfreq": self.sfreq,
                "unit": self.unit, "reference": self.reference, "mean": self.mean.tolist(),
                "scale": self.scale.tolist(),
                "weights": {key: value.detach().cpu().tolist() for key, value in self.network.state_dict().items()}}


def _normalize(X, mean, scale):
    normalized = np.empty(X.shape, dtype=np.float32)
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        try:
            np.subtract(X, mean[None, :, None], out=normalized, casting="unsafe")
            np.divide(normalized, scale[None, :, None], out=normalized, casting="unsafe")
        except FloatingPointError as exc:
            raise ValueError("Neural normalization overflow; explicitly rescale input") from exc
    return normalized


def train_temporal(dataset: EpochDataset, *, train_subjects=None, validation_subjects=None,
                   test_subjects=None, max_epochs=30, patience=5, batch_size=16,
                   learning_rate=.003, seed=42, memory_budget_bytes=512 * 1024 * 1024):
    """Return (model, report) using complete disjoint training/validation/test subjects.

    Defaults reserve the last sorted subject for test and penultimate for
    validation. Validation loss alone chooses checkpoints/learning rate and early
    stopping. Test labels never fit normalization, weights or training decisions.
    CPU training is bounded to one torch thread and restores prior thread/random
    settings after fitting. A seed does not guarantee cross-version bit equality.
    """
    if not isinstance(dataset, EpochDataset):
        raise TypeError("dataset must be an EpochDataset")
    for name, value, low, high in [("max_epochs", max_epochs, 1, 500), ("patience", patience, 1, 100),
                                    ("batch_size", batch_size, 1, 1024), ("seed", seed, 0, 2**32 - 1)]:
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"{name} must be an integer in {low}..{high}")
    if not np.isfinite(learning_rate) or not 0 < learning_rate <= .1:
        raise ValueError("learning_rate must be in (0, .1]")
    if type(memory_budget_bytes) is not int or memory_budget_bytes < 1:
        raise ValueError("Require a positive memory budget")
    subjects = sorted(set(dataset.subjects))
    if len(subjects) < 3:
        raise ValueError("At least three subjects required for disjoint train/validation/test")
    if train_subjects is None and validation_subjects is None and test_subjects is None:
        train_subjects, validation_subjects, test_subjects = subjects[:-2], subjects[-2:-1], subjects[-1:]
    partitions = []
    for values in (train_subjects, validation_subjects, test_subjects):
        if values is None or isinstance(values, (str, bytes)):
            raise ValueError("Supply all three subject sequences or omit all three")
        values = list(values)
        if not values or any(not isinstance(s, str) for s in values) or len(set(values)) != len(values):
            raise ValueError("Partitions require nonempty unique string subject identifiers")
        partitions.append(set(values))
    if any(partitions[a] & partitions[b] for a, b in [(0, 1), (0, 2), (1, 2)]) or set.union(*partitions) != set(subjects):
        raise ValueError("Subject partitions must be disjoint and cover the complete dataset exactly")
    masks = [np.flatnonzero(np.isin(dataset.subjects, list(part))) for part in partitions]
    train, validation, test = masks
    classes = np.unique(dataset.y)
    if set(dataset.y[train]) != set(classes):
        raise ValueError("Training subjects lack a class in the validation/test cohort")
    # Bound normalized copies plus indexed raw-data copies BEFORE allocating them.
    required = int(dataset.X.size * (8 + 4) + dataset.X[0].size * batch_size * 4 * 64)
    if required > memory_budget_bytes:
        raise ValueError("Neural preprocessing and batch estimate exceeds memory budget")
    mean = dataset.X[train].mean(axis=(0, 2))
    scale = dataset.X[train].std(axis=(0, 2))
    if not np.isfinite(mean).all() or not np.isfinite(scale).all() or np.any(scale <= np.finfo(float).tiny):
        raise ValueError("Training channel normalization is undefined for constant/unrepresentable data")
    arrays = [_normalize(dataset.X[indices], mean, scale) for indices in masks]
    labels = [np.searchsorted(classes, dataset.y[indices]).astype(np.int64) for indices in masks]
    torch = _torch()
    old_threads = torch.get_num_threads()
    old_deterministic = torch.are_deterministic_algorithms_enabled()
    old_warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
    started = perf_counter()
    history, best_loss, wait, best_epoch = [], float("inf"), 0, 0
    try:
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            network = _network(dataset.X.shape[1], len(classes))
            optimizer = torch.optim.Adam(network.parameters(), lr=learning_rate)
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, factor=.5, patience=max(1, patience // 2))
            loss_function = torch.nn.CrossEntropyLoss()
            order_generator = torch.Generator().manual_seed(seed)
            tensors = [(torch.from_numpy(X), torch.from_numpy(y)) for X, y in zip(arrays, labels)]
            best_state = None
            for epoch in range(1, max_epochs + 1):
                network.train()
                order = torch.randperm(len(train), generator=order_generator)
                total_loss = 0.
                for offset in range(0, len(order), batch_size):
                    selected = order[offset:offset + batch_size]
                    optimizer.zero_grad(set_to_none=True)
                    loss = loss_function(network(tensors[0][0][selected]), tensors[0][1][selected])
                    if not torch.isfinite(loss):
                        raise ValueError("Training produced a nonfinite loss")
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(network.parameters(), 5., error_if_nonfinite=True)
                    optimizer.step()
                    total_loss += float(loss.detach()) * len(selected)
                network.eval()
                with torch.no_grad():
                    validation_loss = float(loss_function(network(tensors[1][0]), tensors[1][1]))
                if not np.isfinite(validation_loss):
                    raise ValueError("Validation produced a nonfinite loss")
                history.append({"epoch": epoch, "train_loss": total_loss / len(train),
                                "validation_loss": validation_loss,
                                "learning_rate": optimizer.param_groups[0]["lr"]})
                if validation_loss < best_loss - 1e-6:
                    best_loss, best_epoch, wait = validation_loss, epoch, 0
                    best_state = {key: value.detach().clone() for key, value in network.state_dict().items()}
                else:
                    wait += 1
                scheduler.step(validation_loss)
                if wait >= patience:
                    break
            network.load_state_dict(best_state, strict=True)
            model = TemporalModel(network, tuple(classes), dataset.channels, dataset.sfreq,
                                   dataset.unit, dataset.reference, mean, scale)
            metadata = {"sfreq": dataset.sfreq, "unit": dataset.unit,
                        "channels": dataset.channels, "reference": dataset.reference}
            test_probabilities = model.predict_proba(dataset.X[test], **metadata)
            predicted = classes[test_probabilities.argmax(axis=1)]
    finally:
        torch.use_deterministic_algorithms(old_deterministic, warn_only=old_warn_only)
        torch.set_num_threads(old_threads)
    envelope = {"shape": list(dataset.X.shape), "dtype": "<f8", "labels": dataset.y.tolist(),
                "subjects": dataset.subjects.tolist(), "provenance": json.loads(dataset._provenance_json)}
    encoded = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    fingerprint = sha256(len(encoded).to_bytes(8, "big") + encoded + dataset.X.astype("<f8").tobytes()).hexdigest()
    parameter_count = sum(value.numel() for value in network.parameters())
    report = {"schema_version": 1, "architecture": "temporal_conv1d_v1", "seed": seed,
              "data_sha256": fingerprint, "data_fingerprint_schema": "biosignal-neural-epochs-v1",
              "provenance": json.loads(dataset._provenance_json),
              "train_subjects": sorted(partitions[0]), "validation_subjects": sorted(partitions[1]),
              "test_subjects": sorted(partitions[2]),
              "n_train": len(train), "n_validation": len(validation), "n_test": len(test),
              "classes": classes.tolist(), "best_epoch": best_epoch, "epochs_executed": len(history),
              "early_stopped": len(history) < max_epochs, "history": history,
              "test_metrics": _metrics(dataset.y[test], predicted, classes),
              "test_per_subject": [{"subject": subject,
                                     "metrics": _metrics(dataset.y[test][dataset.subjects[test] == subject],
                                                         predicted[dataset.subjects[test] == subject], classes)}
                                    for subject in sorted(partitions[2])],
              "normalization": {"scope": "training subjects only", "mean": mean.tolist(), "scale": scale.tolist()},
              "training": {"optimizer": "Adam", "learning_rate": learning_rate, "batch_size": batch_size,
                           "max_epochs": max_epochs, "patience": patience,
                           "scheduler": "ReduceLROnPlateau(validation_loss)", "gradient_norm_clip": 5.,
                           "checkpoint_selection": "minimum validation loss, delta 1e-6; test labels never select weights"},
              "performance": {"fit_and_test_seconds": perf_counter() - started, "device": "cpu",
                              "torch_threads_during_fit": 1, "parameters": parameter_count,
                              "parameter_bytes_float32": parameter_count * 4,
                              "preprocessing_and_batch_estimated_bytes": required},
              "software": {name: version(name) for name in ("torch", "numpy", "scikit-learn")},
              "limitations": ["Lightweight research baseline, not EEGNet or a physiological/clinical validation.",
                              "Single subject-disjoint holdout; repeat subject protocols and independent cohorts before generalisation claims.",
                              "CPU-only training tested; GPU, edge export and quantization are unverified.",
                              "Memory budget is a preprocessing/batch estimate, not a complete torch/process RSS guarantee."]}
    return model, report


def save_temporal_model(model: TemporalModel, path):
    """Save strict numeric JSON; never overwrite or serialize Python objects."""
    if not isinstance(model, TemporalModel):
        raise TypeError("Expected TemporalModel")
    data = model.to_dict()
    serialized = json.dumps(data, allow_nan=False, separators=(",", ":")) + "\n"
    with Path(path).open("x", encoding="utf-8") as output:
        output.write(serialized)


def _finite_numeric_tree(value):
    if isinstance(value, list):
        return all(_finite_numeric_tree(item) for item in value)
    return _real_json_number(value)


def load_temporal_model(path, max_bytes=8 * 1024 * 1024):
    """Load one fixed architecture from bounded JSON; no torch.load or pickle."""
    if type(max_bytes) is not int or not 1 <= max_bytes <= 32 * 1024 * 1024:
        raise ValueError("Checkpoint byte limit must be in 1..32 MiB")
    with Path(path).open("rb") as stream:
        raw = stream.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("Neural checkpoint exceeds byte limit")
    data = json.loads(raw, object_pairs_hook=_unique_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
    fields = {"schema_version", "format", "architecture", "classes", "channels", "sfreq",
              "unit", "reference", "mean", "scale", "weights"}
    if not isinstance(data, dict) or set(data) != fields or type(data["schema_version"]) is not int or data["schema_version"] != 1 or data["format"] != "biosignal-temporal-json" or data["architecture"] != "temporal_conv1d_v1":
        raise ValueError("Unsupported neural checkpoint schema")
    if any(not isinstance(data[key], list) or any(not isinstance(s, str) for s in data[key])
           for key in ("classes", "channels")):
        raise ValueError("Classes and channels must be JSON arrays of strings")
    if not _real_json_number(data["sfreq"]) or any(not isinstance(data[key], list) or not _finite_numeric_tree(data[key]) for key in ("mean", "scale")):
        raise ValueError("Normalization and sampling frequency require finite JSON numbers")
    torch = _torch()
    # All sizes are bounded before allocation and the only architecture is local.
    with torch.random.fork_rng(devices=[]):
        network = _network(len(data["channels"]), len(data["classes"]))
    expected = network.state_dict()
    if not isinstance(data["weights"], dict) or set(data["weights"]) != set(expected):
        raise ValueError("Neural checkpoint has unexpected tensor names")
    tensors = {}
    for name, template in expected.items():
        raw_values = data["weights"][name]
        if not isinstance(raw_values, list) or not _finite_numeric_tree(raw_values):
            raise ValueError("Weights must be finite JSON numbers, excluding booleans")
        values = np.asarray(raw_values, dtype=float)
        if values.shape != tuple(template.shape):
            raise ValueError("Neural tensor shape does not match fixed architecture")
        tensor = torch.tensor(values, dtype=template.dtype)
        if not torch.isfinite(tensor).all():
            raise ValueError("Weight conversion exceeds architecture precision")
        tensors[name] = tensor
    network.load_state_dict(tensors, strict=True)
    return TemporalModel(network, data["classes"], data["channels"], data["sfreq"],
                          data["unit"], data["reference"], data["mean"], data["scale"])
