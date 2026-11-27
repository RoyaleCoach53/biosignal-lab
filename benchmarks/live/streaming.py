"""Synthetic CPU processing benchmark; never device-to-display latency evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import time
import tracemalloc

import numpy as np
import scipy
from scipy.signal import butter

from biosignal_lab.live import LiveProcessor, SimulatedDevice, StreamInfo


def run(channels=8, sfreq=1000, block_samples=100, blocks=300):
    info = StreamInfo(sfreq, tuple(f"CH{i}" for i in range(channels)), ("uV",)*channels, clock="simulated_seconds")
    source = SimulatedDevice(info)
    processor = LiveProcessor(info, butter(4, [1, 40], btype="bandpass", fs=sfreq, output="sos"))
    for _ in range(30):
        processor.process(source.read(block_samples))
    latencies = []
    tracemalloc.start()
    beginning = time.perf_counter()
    for _ in range(blocks):
        block = source.read(block_samples)
        start = time.perf_counter()
        processor.process(block)
        latencies.append(time.perf_counter()-start)
    elapsed = time.perf_counter()-beginning
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    source.close()
    cpu = platform.processor()
    if not cpu and Path("/proc/cpuinfo").exists():
        cpu = next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name")), "unknown")
    root = Path(__file__).resolve().parents[2]
    source_files = [Path(__file__), *sorted((root / "src/biosignal_lab/live").glob("*.py"))]
    return {"scope": "Deterministic synthetic acquisition, causal SOS and sliding Welch PSD; no physical hardware or wall-clock pacing",
            "source_sha256": {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files},
            "host": {"os": platform.system(), "architecture": platform.machine(), "cpu": cpu, "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__},
            "workload": {"channels": channels, "sfreq_hz": sfreq, "block_samples": block_samples, "blocks": blocks, "warmup_blocks": 30},
            "cpu_processing_p50_ms": float(np.percentile(latencies, 50)*1000),
            "cpu_processing_p95_ms": float(np.percentile(latencies, 95)*1000),
            "cpu_processing_max_ms": float(np.max(latencies)*1000),
            "samples_per_second_including_simulation": blocks*block_samples/elapsed,
            "tracemalloc_peak_bytes": peak,
            "limitations": ["Tracemalloc is Python-tracked allocator peak, not process RSS", "Timing includes tracemalloc overhead and excludes acquisition/network/display", "Container scheduling affects timings; no guaranteed real-time deadlines"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error("Output must be new; existing evidence is preserved")
    report = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
