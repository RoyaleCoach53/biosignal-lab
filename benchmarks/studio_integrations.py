"""Run actual simulated Live and subject-grouped AI DAGs; preserve existing reports."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import time
import tracemalloc

from biosignal_lab.studio import Workflow, Executor, builtin_registry


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.exists() or args.output.is_symlink():
        parser.error("Use a nonexistent report path; previous evidence is preserved")
    root = Path(__file__).resolve().parents[1]
    observations = {}
    executor = Executor(builtin_registry())
    for name in ("live_to_report", "grouped_ai"):
        workflow = Workflow.from_json((root / "examples/workflows" / f"{name}.json").read_text())
        tracemalloc.start()
        tick = time.perf_counter()
        execution = executor.execute(workflow)
        seconds = time.perf_counter() - tick
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        observations[name] = {"workflow_sha256": workflow.digest,
                              "source_sha256": execution.manifest["source_sha256"],
                              "dependencies": execution.manifest["dependencies"],
                              "seconds": seconds, "python_allocator_peak_bytes": peak,
                              "node_count": len(execution.manifest["nodes"])}
        if name == "live_to_report":
            observations[name]["diagnostics"] = execution.outputs["acquisition"]["diagnostics"]
            observations[name]["samples_analyzed"] = execution.outputs["summary"]["out"]["n_samples"]
        else:
            observations[name]["evaluation"] = execution.outputs["evaluation"]["out"]
            observations[name]["portable_model_format"] = execution.outputs["portable_model"]["out"]["format"]
            observations[name]["predictions"] = len(execution.outputs["fitted_predictions"]["out"]["predictions"])
    report = {"schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
              "host": {"os": platform.system(), "architecture": platform.machine(), "python": platform.python_version()},
              "scope": "Synthetic verification only. Virtual acquisition has no physical device or human recordings; AI distinguishes generated oscillations and is not evidence of physiological classification. Timing covers this one local process. Python allocator peaks exclude some native memory and are not process RSS.",
              "observations": observations}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({name: {k: value for k, value in item.items() if k in {"seconds", "python_allocator_peak_bytes", "node_count", "samples_analyzed", "predictions"}}
                      for name, item in observations.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
