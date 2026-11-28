"""Validate and execute versioned scientific workflows without the graphical UI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import Workflow, Executor, builtin_registry, NodeExecutionError, ExecutionCancelled


def read_workflow(path: Path) -> Workflow:
    if path.stat().st_size > 1_000_000:
        raise ValueError("Workflow exceeds one megabyte import limit")
    return Workflow.from_json(path.read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "run", "python"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("workflow", type=Path)
        if command == "run":
            command_parser.add_argument("--output", type=Path, required=True,
                                        help="New directory for manifest and JSON/HTML outputs; existing directories are preserved")
            command_parser.add_argument("--source-root", type=Path,
                                        help="Explicitly allow CSV reads within this directory")
            command_parser.add_argument("--workers", type=int, default=1, choices=range(1, 5),
                                        help="Overlap reviewed pure nodes with 1..4 workers; default serial")
    args = parser.parse_args(argv)
    try:
        workflow = read_workflow(args.workflow)
        executor = Executor(builtin_registry(), source_root=getattr(args, "source_root", None),
                            max_workers=getattr(args, "workers", 1))
        order = executor.validate(workflow)
        if args.command == "validate":
            print(json.dumps({"valid": True, "workflow_sha256": workflow.digest,
                              "order": [node.id for node in order]}))
        elif args.command == "python":
            print(workflow.python_source(), end="")
        else:
            # Reserve a fresh output location before executing any input node.
            args.output.mkdir(parents=True, exist_ok=False)
            result = executor.execute(workflow)
            with (args.output / "manifest.json").open("x", encoding="utf-8") as handle:
                handle.write(result.manifest_json() + "\n")
            for node in workflow.nodes:
                definition = executor.registry[node.kind]
                for port, value in result.outputs[node.id].items():
                    kind = definition.outputs[port].kind
                    if kind not in ("json", "html"):
                        continue
                    suffix = ".json" if kind == "json" else ".html"
                    text = json.dumps(value, indent=2, allow_nan=False) if kind == "json" else value
                    with (args.output / (node.id + "-" + port + suffix)).open("x", encoding="utf-8") as handle:
                        handle.write(text + "\n")
            print(json.dumps({"passed": True, "workflow_sha256": workflow.digest,
                              "nodes_executed": len(order)}))
    except (OSError, ValueError, NodeExecutionError, ExecutionCancelled) as exc:
        print(f"Workflow failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
