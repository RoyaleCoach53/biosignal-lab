"""Real Live/AI adapters; unavailable optional packages do not create stub nodes."""
from __future__ import annotations

from importlib.util import find_spec
import math

import numpy as np

from ..models import Recording
from .nodes import _parameters, _empty
from .runtime import Definition, Port, WorkflowError, ExecutionCancelled


def _live_validate(p):
    _parameters(p, {"duration_s": "number", "sfreq": "number", "n_channels": "integer",
                    "chunk_samples": "integer", "frequency_hz": "number", "seed": "integer",
                    "modality": ("eeg", "emg")})
    if not 1 <= p.get("duration_s", 4) <= 60 or not 40 <= p.get("sfreq", 250) <= 4000:
        raise ValueError("Simulated acquisition requires 1..60 seconds and 40..4000 Hz")
    if not 1 <= p.get("n_channels", 2) <= 128 or not 1 <= p.get("chunk_samples", 50) <= 10000:
        raise ValueError("Use 1..128 channels and 1..10000 samples per chunk")
    if not 0 < p.get("frequency_hz", 10) < p.get("sfreq", 250) / 2 or p.get("seed", 42) < 0:
        raise ValueError("Positive simulation frequency must lie below Nyquist; seed must be nonnegative")


def _live(i, p, c):
    from ..live import StreamInfo, SimulatedDevice, LiveProcessor
    sfreq, n_channels = p.get("sfreq", 250), p.get("n_channels", 2)
    count = round(p.get("duration_s", 4) * sfreq)
    if count * n_channels > c.limits.max_signal_values:
        raise WorkflowError("Simulated acquisition exceeds value limit before allocation")
    if math.ceil(count / p.get("chunk_samples", 50)) > 4096:
        raise WorkflowError("Studio acquisition is limited to 4096 blocks; increase chunk_samples")
    channels = tuple(f"LiveCh{k + 1}" for k in range(n_channels))
    info = StreamInfo(sfreq, channels, ("uV",) * n_channels, p.get("modality", "eeg"), "simulated_device")
    device = SimulatedDevice(info, seed=p.get("seed", 42), frequency=p.get("frequency_hz", 10))
    processor = LiveProcessor(info, window_s=min(2, p.get("duration_s", 4)), warmup_s=0)
    chunks, timestamps = [], []
    diagnostics = []
    try:
        for start in range(0, count, p.get("chunk_samples", 50)):
            if c.cancel.is_set():
                raise ExecutionCancelled("Simulated acquisition cancelled between chunks")
            block = device.read(min(p.get("chunk_samples", 50), count - start))
            live = processor.process(block)
            chunks.append(live.block.data)
            timestamps.append(live.block.timestamps)
            diagnostics.append(live.diagnostics)
    finally:
        device.close()
    times = np.concatenate(timestamps)
    signal = Recording(np.concatenate(chunks, axis=1), sfreq, channels, info.modality,
                       f"simulated_live_seed_{p.get('seed', 42)}")
    return {"signal": signal, "diagnostics": {
        "scope": "Simulated device with virtual sample clock; CPU timings exclude physical acquisition and display latency.",
        "clock": info.clock, "sfreq": sfreq, "channels": list(channels), "units": list(info.units),
        "first_timestamp": float(times[0]), "last_timestamp": float(times[-1]),
        "samples": count, "blocks": len(chunks), "final": diagnostics[-1],
        "max_processing_seconds": max(item["processing_seconds"] for item in diagnostics)}}


def _ai_demo_validate(p):
    _parameters(p, {"seed": "integer", "n_subjects": "integer", "trials_per_subject": "integer"})
    if not 3 <= p.get("n_subjects", 4) <= 20 or not 4 <= p.get("trials_per_subject", 8) <= 40 or p.get("seed", 42) < 0:
        raise ValueError("Use 3..20 synthetic subjects, 4..40 trials per subject, nonnegative seed")


def _ai_demo(i, p, c):
    from ..ai.demo import synthetic_feature_dataset
    parameters = {"n_subjects": 4, "trials_per_subject": 8} | p
    if parameters["n_subjects"] * parameters["trials_per_subject"] * 500 > c.limits.max_signal_values:
        raise WorkflowError("Synthetic AI epochs exceed value limit before allocation")
    return {"out": synthetic_feature_dataset(**parameters)}


def _ai_evaluate_validate(p):
    _parameters(p, {"model": ("lda", "qda", "logistic", "svm", "random_forest", "knn", "gradient_boosting"),
                    "cv": ("loso", "group"), "n_splits": "integer", "seed": "integer",
                    "bootstrap_samples": "integer"})
    if not 2 <= p.get("n_splits", 4) <= 20 or not 100 <= p.get("bootstrap_samples", 200) <= 2000 or p.get("seed", 42) < 0:
        raise ValueError("Use 2..20 splits, 100..2000 subject bootstrap samples, nonnegative seed")


def _ai_evaluate(i, p, c):
    from ..ai import evaluate_grouped
    return {"out": evaluate_grouped(i["dataset"], **({"n_splits": 4, "bootstrap_samples": 200} | p))}


def _ai_train_validate(p):
    _parameters(p, {"model": ("lda", "logistic"), "seed": "integer"})
    if p.get("seed", 42) < 0:
        raise ValueError("Seed must be nonnegative")


def _ai_train(i, p, c):
    from ..ai import train_linear
    return {"out": train_linear(i["dataset"], **p)}


def _ai_predict(i, p, c):
    model, dataset = i["model"], i["dataset"]
    if model.feature_names != dataset.feature_names:
        raise WorkflowError("Inference feature names/order must exactly match the portable model")
    return {"out": {"predictions": model.predict(dataset.X).tolist(),
                    "probabilities": model.predict_proba(dataset.X).tolist(),
                    "classes": list(model.classes), "subjects": dataset.subjects.tolist(),
                    "dataset_provenance": dataset.provenance,
                    "scope": "Model predictions only. If training and prediction use the same dataset, these are fitted predictions; use grouped evaluation for out-of-subject performance."}}


def _epoch_validate(p):
    _parameters({k: v for k, v in p.items() if k != "events"}, {"duration_s": "number"})
    if not 0 < p.get("duration_s", 2) <= 60 or not isinstance(p.get("events"), list) or not 2 <= len(p["events"]) <= 1000:
        raise ValueError("Epoch features need duration_s in (0,60] and 2..1000 explicit events")
    for event in p["events"]:
        if (not isinstance(event, dict) or set(event) != {"sample", "label", "subject"}
                or type(event["sample"]) is not int or event["sample"] < 0
                or any(not isinstance(event[key], str) or not event[key] or len(event[key]) > 128 for key in ("label", "subject"))):
            raise ValueError("Each event needs a nonnegative integer sample and explicit bounded label/subject strings")


def _epoch_features(i, p, c):
    from ..ai import FeatureDataset, extract_epoch_features
    signal = i["signal"]
    count = round(p.get("duration_s", 2) * signal.sfreq)
    events = p["events"]
    if count < 16 or len(events) * count * len(signal.channels) > c.limits.max_signal_values:
        raise WorkflowError("Epoch sample count is too short or exceeds configured allocation limit")
    if any(event["sample"] + count > signal.data_uv.shape[1] for event in events):
        raise WorkflowError("Epoch extends beyond recording")
    ordered = sorted(events, key=lambda event: event["sample"])
    for first, second in zip(ordered, ordered[1:]):
        if second["sample"] < first["sample"] + count and first["subject"] != second["subject"]:
            raise WorkflowError("Overlapping samples cannot be assigned to different subject groups")
    # Metadata are supplied by the researcher, never inferred from signal shape.
    epochs = np.stack([signal.data_uv[:, event["sample"]:event["sample"] + count] for event in events])
    X, names = extract_epoch_features(epochs, signal.sfreq, signal.modality)
    dataset = FeatureDataset(X, np.array([e["label"] for e in events]), np.array([e["subject"] for e in events]), names,
                             {"source": signal.source, "unit": "uV", "sfreq": signal.sfreq,
                              "duration_s": count / signal.sfreq, "events": events,
                              "scope": "Labels/subject identity supplied explicitly by workflow author; not physiologically inferred or independently verified."})
    return {"out": dataset}


def register_research_nodes(registry):
    if find_spec("biosignal_lab.live") is not None:
        # Import validates availability of the actual implementation before exposure.
        from ..live import SimulatedDevice
        registry.register(Definition("live_simulate", {}, {"signal": Port("recording", unit="uV"),
                                                            "diagnostics": Port("json")},
                                     _live, _live_validate, pure=False,
                                     description="Acquire deterministic simulated blocks; measured CPU monitor timings, no physical hardware claim"), trusted=True)
    if find_spec("biosignal_lab.ai") is None or find_spec("sklearn") is None:
        return
    from ..ai import FeatureDataset, evaluate_grouped
    dataset = Port("dataset")
    model = Port("linear_model")
    for definition in [
        Definition("ai_demo", {}, {"out": dataset}, _ai_demo, _ai_demo_validate,
                   description="Seeded synthetic oscillation classes with explicit subject groups; not a physiological task"),
        Definition("epoch_features", {"signal": Port("recording", unit="uV")}, {"out": dataset},
                   _epoch_features, _epoch_validate,
                   description="Extract EEG/EMG epoch features using explicitly supplied sample, class and subject metadata"),
        Definition("ai_evaluate", {"dataset": dataset}, {"out": Port("json")}, _ai_evaluate,
                   _ai_evaluate_validate, pure=False,
                   description="Subject-disjoint cross-validation, group-bootstrap intervals and measured CPU timings"),
        Definition("ai_train", {"dataset": dataset}, {"out": model}, _ai_train, _ai_train_validate,
                   description="Fit portable affine LDA/logistic classifier; fitting is not independent evaluation"),
        Definition("ai_model_json", {"model": model}, {"out": Port("json")},
                   lambda i, p, c: {"out": i["model"].to_dict()}, _empty,
                   description="Export safe validated coefficients as JSON, never pickle"),
        Definition("ai_predict", {"model": model, "dataset": dataset}, {"out": Port("json")},
                   _ai_predict, _empty,
                   description="Actual portable model prediction with exact feature-name/order checks"),
    ]:
        registry.register(definition, trusted=True)
