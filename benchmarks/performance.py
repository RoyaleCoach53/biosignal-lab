"""Synthetic in-memory timings and traced allocation peaks, not process RSS."""
import argparse
import json
import os
from pathlib import Path
import platform
import statistics
import time
import tracemalloc

from biosignal_lab import __version__, analyze
from biosignal_lab.simulate import synthetic_recording


def benchmark():
    records = []
    for channels, seconds, fs in [(4, 30, 250), (8, 60, 250), (16, 60, 500)]:
        recording = synthetic_recording(n_channels=channels, duration_s=seconds, sfreq=fs, seed=42)
        analyze(recording)
        elapsed, peaks = [], []
        for _ in range(3):
            tracemalloc.start()
            started = time.perf_counter()
            analyze(recording)
            elapsed.append(time.perf_counter() - started)
            peaks.append(tracemalloc.get_traced_memory()[1])
            tracemalloc.stop()
        records.append({"channels": channels, "duration_s": seconds, "sfreq_hz": fs,
                        "input_bytes": recording.data_uv.nbytes, "warmups": 1, "repetitions": 3,
                        "median_seconds_with_tracing": statistics.median(elapsed),
                        "min_seconds": min(elapsed), "max_seconds": max(elapsed),
                        "median_peak_traced_bytes": statistics.median(peaks)})
    return {"version": __version__, "python": platform.python_version(), "platform": platform.platform(),
            "machine": platform.machine(), "logical_cpu_count": os.cpu_count(), "records": records,
            "scope": "Synthetic analyze() only; inputs allocated before measurement. Tracing adds overhead. Peaks are allocator-traced memory, not process RSS, and may miss native allocations. No throughput or cross-machine speedup claim."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("performance.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(benchmark(), indent=2)+"\n", encoding="utf-8", newline="\n")
    print("Recorded three synthetic timing/allocation workloads.")
