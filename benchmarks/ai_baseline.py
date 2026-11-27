"""Measure a synthetic grouped baseline, shuffled-label control and JSON inference.

This benchmark is not evidence of physiological or clinical accuracy. The output
must be a new path so previous measurements are never overwritten.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
from time import perf_counter_ns
import tracemalloc

import numpy as np

from biosignal_lab.ai import FeatureDataset, evaluate_grouped, train_linear
from biosignal_lab.ai.demo import synthetic_feature_dataset


def benchmark(seed=42):
    dataset = synthetic_feature_dataset(seed)
    tracemalloc.start()
    start = perf_counter_ns()
    report = evaluate_grouped(dataset, model="lda", seed=seed)
    elapsed_ms = (perf_counter_ns() - start) / 1e6
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rng = np.random.default_rng(seed + 1)
    shuffled = FeatureDataset(dataset.X, rng.permutation(dataset.y), dataset.subjects,
                              dataset.feature_names, {"scope": "Shuffled-label synthetic control"})
    control = evaluate_grouped(shuffled, model="lda", seed=seed)
    model = train_linear(dataset)
    model.predict(dataset.X[:1])
    times = []
    for _ in range(200):
        start = perf_counter_ns()
        model.predict(dataset.X[:1])
        times.append((perf_counter_ns() - start) / 1e6)
    cpu = platform.processor() or "not reported by platform"
    cpu_info = Path("/proc/cpuinfo")
    if cpu_info.is_file():
        cpu = next((line.split(":", 1)[1].strip() for line in cpu_info.read_text().splitlines()
                    if line.startswith("model name")), cpu)
    root = Path(__file__).resolve().parents[1]
    sources = [Path(__file__).relative_to(root), *sorted(Path("src/biosignal_lab/ai").glob("*.py"))]
    return {"schema_version": 1, "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "Deterministic synthetic oscillation classification; not a physiological task or clinical validation.",
            "hardware": {"cpu": cpu, "logical_cpus": os.cpu_count(), "architecture": platform.machine(),
                         "os": platform.system(), "python": platform.python_version()},
            "grouped_baseline": report, "shuffled_label_control": control,
            "measurements": {"loso_evaluation_ms": elapsed_ms,
                             "tracemalloc_python_peak_bytes": peak,
                             "tracemalloc_scope": "Python-traced allocation peak during evaluation; not process RSS or native BLAS memory.",
                             "json_model_bytes": len(json.dumps(model.to_dict(), allow_nan=False).encode()),
                             "inference_batch_size": 1, "inference_repetitions": 200,
                             "inference_median_ms": float(np.median(times)),
                             "inference_p95_ms": float(np.quantile(times, .95)),
                             "inference_scope": "Warm in-process CPU JSON model prediction; excludes acquisition, features, IO and model loading."},
            "source_sha256": {str(path): sha256((root / path).read_bytes()).hexdigest() for path in sources}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    # Reserve output before any computation, rejecting stale reports first.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with args.output.open("x", encoding="utf-8") as output:
            created = True
            result = benchmark(args.seed)
            output.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    except BaseException:
        if created:
            args.output.unlink(missing_ok=True)
        raise
    print(json.dumps(result["measurements"], indent=2))


if __name__ == "__main__":
    main()
