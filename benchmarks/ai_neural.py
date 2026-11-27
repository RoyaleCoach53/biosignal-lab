"""Actual bounded CPU Conv1D training on synthetic spatial variance patterns."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import subprocess
from time import perf_counter_ns
import tracemalloc

import numpy as np

from biosignal_lab.ai import train_temporal
from biosignal_lab.ai.demo import synthetic_epoch_dataset


def benchmark(seed=42, max_epochs=25):
    import torch
    data = synthetic_epoch_dataset(seed=seed)
    tracemalloc.start()
    model, report = train_temporal(data, seed=seed, max_epochs=max_epochs, patience=5)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    metadata = {"sfreq": data.sfreq, "unit": data.unit, "channels": data.channels, "reference": data.reference}
    old_threads = torch.get_num_threads()
    try:
        torch.set_num_threads(1)
        model.predict_proba(data.X[:1], **metadata)
        times = []
        for _ in range(100):
            start = perf_counter_ns()
            model.predict_proba(data.X[:1], **metadata)
            times.append((perf_counter_ns() - start) / 1e6)
    finally:
        torch.set_num_threads(old_threads)
    root = Path(__file__).resolve().parents[1]
    cpu = platform.processor() or "not reported by platform"
    cpu_info = Path("/proc/cpuinfo")
    if cpu_info.is_file():
        cpu = next((line.split(":", 1)[1].strip() for line in cpu_info.read_text().splitlines()
                    if line.startswith("model name")), cpu)
    sources = [Path(__file__).relative_to(root), *sorted((root / "src/biosignal_lab/ai").glob("*.py"))]
    source_hashes = {}
    for source in sources:
        path = source if source.is_absolute() else root / source
        source_hashes[str(path.relative_to(root))] = sha256(path.read_bytes()).hexdigest()
    return {"schema_version": 1, "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "Synthetic spatial covariance patterns, not motor imagery or clinical performance.",
            "hardware": {"cpu": cpu, "logical_cpus": os.cpu_count(),
                         "os": platform.system(), "architecture": platform.machine()},
            "experiment": report,
            "measurements": {"single_epoch_inference_median_ms": float(np.median(times)),
                             "single_epoch_inference_p95_ms": float(np.quantile(times, .95)),
                             "inference_repetitions": 100, "inference_torch_threads": 1,
                             "inference_scope": "Warm CPU inference includes normalization; excludes IO, acquisition and loading.",
                             "json_model_bytes": len(json.dumps(model.to_dict()).encode()),
                             "tracemalloc_python_peak_bytes": peak,
                             "memory_scope": "Python-traced training allocation peak, not process RSS or all native torch allocations."},
            "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
            "source_sha256": source_hashes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-epochs", type=int, default=25)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with args.output.open("x", encoding="utf-8") as output:
            created = True
            report = benchmark(args.seed, args.max_epochs)
            output.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    except BaseException:
        if created:
            args.output.unlink(missing_ok=True)
        raise
    print(json.dumps({"test_metrics": report["experiment"]["test_metrics"],
                      "measurements": report["measurements"]}, indent=2))


if __name__ == "__main__":
    main()
