"""Measure a real synthetic Studio graph; refuses to replace prior evidence."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import time
import tracemalloc

from biosignal_lab.studio import Workflow, Executor, builtin_registry


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists() or args.output.is_symlink():
        parser.error("Choose a new output file; existing scientific evidence is preserved")
    workflow = Workflow.from_json((Path(__file__).resolve().parents[1] / "examples/workflows/eeg_quality.json").read_text())
    executor = Executor(builtin_registry())
    observations = []
    for label in ("cold_execution", "same_process_repeat"):
        tracemalloc.start()
        started = time.perf_counter()
        result = executor.execute(workflow)
        elapsed = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        assert result.outputs["summary"]["out"]["n_samples"] == 2500
        observations.append({"run": label, "seconds": elapsed,
                             "python_tracemalloc_peak_bytes": peak,
                             "cache_hits": sum(n["cache_hit"] for n in result.manifest["nodes"]),
                             "nodes": len(result.manifest["nodes"]),
                             "output_sha256": {n["node"]: n["output_sha256"] for n in result.manifest["nodes"]
                                               if n["kind"] != "html"}})
    report = {"schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Synthetic local in-memory DAG; 2 EEG channels, 250 Hz, 10 seconds. Python allocator peaks exclude some native memory and are not process RSS. Two runs do not establish a throughput/latency distribution or hardware compatibility.",
              "host": {"os": platform.system(), "architecture": platform.machine(), "python": platform.python_version()},
              "workflow_sha256": workflow.digest, "source_sha256": result.manifest["source_sha256"],
              "dependencies": result.manifest["dependencies"], "limits": asdict(executor.limits),
              "runs": observations,
              "scientific_outputs_reproduced": observations[0]["output_sha256"] == observations[1]["output_sha256"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"scientific_outputs_reproduced": report["scientific_outputs_reproduced"],
                      "runs": [{k: v for k, v in run.items() if k != "output_sha256"} for run in observations]}))
    return 0 if report["scientific_outputs_reproduced"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
