"""Execution, contracts, cache and hostile definition regression coverage."""
from __future__ import annotations

import json
from pathlib import Path
import threading

import numpy as np
import pytest

from biosignal_lab.studio import (Workflow, Node, Connection, Executor, Cache,
                                  builtin_registry, Limits, Registry, Definition, Port,
                                  WorkflowError, NodeExecutionError, ExecutionCancelled)
from biosignal_lab.studio.cli import main
from biosignal_lab.studio.runtime import fingerprint


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "examples/workflows/eeg_quality.json"


def example():
    return Workflow.from_json(TEMPLATE.read_text())


def test_real_workflow_reproduces_pipeline_and_manifest():
    workflow = example()
    execution = Executor(builtin_registry()).execute(workflow)
    summary = execution.outputs["summary"]["out"]
    assert summary["n_channels"] == 2 and summary["n_samples"] == 2500
    assert len(execution.outputs["bandpower"]["out"]) == 2
    assert "<!DOCTYPE html>" in execution.outputs["report"]["out"]
    manifest = json.loads(execution.manifest_json())
    assert manifest["workflow_sha256"] == workflow.digest
    assert len(manifest["nodes"]) == 6
    assert all(len(n["output_sha256"]) == 64 for n in manifest["nodes"])
    assert "data_uv" not in execution.manifest_json()


def test_roundtrip_and_generated_python_are_data_only():
    workflow = Workflow((Node("demo", "simulate", {"seed": 3}),), name="'\nraise RuntimeError('bad')\n")
    assert Workflow.from_json(workflow.to_json()).digest == workflow.digest
    namespace = {}
    exec(compile(workflow.python_source(), "generated", "exec"), namespace)
    assert namespace["workflow"].name == workflow.name
    assert len(namespace["result"].outputs["demo"]["out"].channels) == 2


@pytest.mark.parametrize("definition", [
    '{"schema_version":2,"nodes":[{"id":"a","kind":"simulate"}]}',
    '{"nodes":[{"id":"../outside","kind":"simulate"}]}',
    '{"nodes":[{"id":"a","kind":"simulate","parameters":{"seed":NaN}}]}',
    '{"nodes":[{"id":"a","kind":"simulate"}],"nodes":[]}',
    '{"nodes":[{"id":"a","kind":"simulate","code":"print(1)"}]}',
    '{"nodes":[{"id":"a","kind":"simulate"},{"id":"a","kind":"simulate"}]}',
    '{"nodes":[{"id":"a","kind":"simulate","inputs":{"in":"not-a-link"}}]}',
])
def test_malformed_and_executable_schema_rejected(definition):
    with pytest.raises(ValueError):
        Workflow.from_json(definition)


def test_import_size_and_graph_limits():
    with pytest.raises(ValueError, match="size limit"):
        Workflow.from_json(example().to_json(), max_bytes=20)
    with pytest.raises(WorkflowError, match="node limit"):
        Executor(builtin_registry(), limits=Limits(max_nodes=2)).validate(example())


def test_type_mismatch_cycle_and_missing_ports_are_diagnosed():
    executor = Executor(builtin_registry())
    with pytest.raises(WorkflowError, match="cannot connect"):
        executor.validate(Workflow((Node("demo", "simulate"), Node("report", "html", inputs={"analysis": Connection("demo")}))))
    with pytest.raises(WorkflowError, match="needs input"):
        executor.validate(Workflow((Node("analysis", "analyze"),)))
    with pytest.raises(WorkflowError, match="missing upstream"):
        executor.validate(Workflow((Node("analysis", "analyze", inputs={"signal": Connection("absent")}),)))
    with pytest.raises(WorkflowError, match="Cycle"):
        executor.validate(Workflow((Node("a", "analyze", inputs={"signal": Connection("b")}),
                                    Node("b", "processed", inputs={"analysis": Connection("a")}))))


def test_unregistered_plugin_is_never_imported():
    with pytest.raises(WorkflowError, match="Unregistered"):
        Executor(builtin_registry()).validate(Workflow((Node("bad", "os_system"),)))
    definition = Definition("plugin", {}, {"out": Port("json")}, lambda i, p, c: {"out": 1}, lambda p: None)
    with pytest.raises(PermissionError, match="trusted=True"):
        Registry().register(definition)


def test_unknown_and_illtyped_parameters_rejected_before_execution():
    executor = Executor(builtin_registry())
    for parameters in ({"n_channels": True}, {"seed": -1}, {"sfreq": "250"}, {"bogus": 1}):
        with pytest.raises(WorkflowError):
            executor.validate(Workflow((Node("demo", "simulate", parameters),)))


def test_runtime_modality_and_frequency_contracts():
    executor = Executor(builtin_registry())
    workflow = Workflow((Node("demo", "simulate", {"modality": "emg"}),
                         Node("spectrum", "psd", inputs={"signal": Connection("demo")}),
                         Node("bands", "bands", inputs={"spectrum": Connection("spectrum")})))
    with pytest.raises(NodeExecutionError, match="Modality mismatch") as error:
        executor.execute(workflow)
    assert error.value.node_id == "bands"
    registry = builtin_registry()
    registry.register(Definition("fixed_rate", {"signal": Port("recording", sfreq=500)},
                                  {"out": Port("json")}, lambda i, p, c: {"out": 1}, lambda p: None), trusted=True)
    with pytest.raises(NodeExecutionError, match="Sampling rate mismatch"):
        Executor(registry).execute(Workflow((Node("demo", "simulate"),
                                           Node("fixed", "fixed_rate", inputs={"signal": Connection("demo")}))))


def test_resource_limit_checked_before_simulation_allocation():
    executor = Executor(builtin_registry(), limits=Limits(max_signal_values=100))
    with pytest.raises(NodeExecutionError, match="before allocation"):
        executor.execute(Workflow((Node("demo", "simulate"),)))
    with pytest.raises(NodeExecutionError, match="retained-output"):
        Executor(builtin_registry(), limits=Limits(max_output_bytes=100)).execute(example())


def test_cache_keys_include_data_parameters_and_detach_mutable_arrays():
    executor = Executor(builtin_registry(), cache=Cache(max_bytes=1_000_000))
    workflow = Workflow((Node("demo", "simulate", {"seed": 1}),))
    first = executor.execute(workflow)
    original = first.outputs["demo"]["out"].data_uv.copy()
    first.outputs["demo"]["out"].data_uv[:] = 999
    second = executor.execute(workflow)
    np.testing.assert_array_equal(second.outputs["demo"]["out"].data_uv, original)
    assert second.manifest["nodes"][0]["cache_hit"]
    changed = executor.execute(Workflow((Node("demo", "simulate", {"seed": 2}),)))
    assert not changed.manifest["nodes"][0]["cache_hit"]
    assert changed.manifest["nodes"][0]["output_sha256"] != second.manifest["nodes"][0]["output_sha256"]


def test_fingerprints_frame_nested_mapping_boundaries():
    assert fingerprint({"a": {"b": 1}, "c": 2}) != fingerprint({"a": {"b": 1, "c": 2}})
    assert fingerprint({"a": [1, 2]}) != fingerprint({"a": [[1], 2]})
    assert fingerprint({"a": {"b": 1}, "c": 2}) == fingerprint({"c": 2, "a": {"b": 1}})


def test_cancellation_before_and_after_node_and_progress():
    token = threading.Event()
    token.set()
    with pytest.raises(ExecutionCancelled):
        Executor(builtin_registry()).execute(example(), cancel=token)
    token.clear()
    events = []
    def progress(node, status):
        events.append((node, status))
        if status == "completed":
            token.set()
    with pytest.raises(ExecutionCancelled):
        Executor(builtin_registry()).execute(example(), cancel=token, progress=progress)
    assert events == [("demo", "running"), ("demo", "completed")]


def test_failed_node_retry_reuses_only_completed_pure_outputs():
    registry = builtin_registry()
    attempts = []
    def flaky(inputs, parameters, context):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("simulated transient failure")
        return {"out": {"samples": inputs["signal"].data_uv.shape[1]}}
    registry.register(Definition("reviewed_retry", {"signal": Port("recording")},
                                  {"out": Port("json")}, flaky, lambda p: None, pure=False), trusted=True)
    executor = Executor(registry)
    workflow = Workflow((Node("demo", "simulate"),
                         Node("retry", "reviewed_retry", inputs={"signal": Connection("demo")})))
    with pytest.raises(NodeExecutionError, match="simulated transient failure"):
        executor.execute(workflow)
    result = executor.execute(workflow)
    assert result.manifest["nodes"][0]["cache_hit"]
    assert not result.manifest["nodes"][1]["cache_hit"]
    assert result.outputs["retry"]["out"]["samples"] == 2500


def test_cache_is_bounded_and_plugin_mutation_cannot_corrupt_parent():
    registry = builtin_registry()
    def mutate(inputs, parameters, context):
        inputs["signal"].data_uv[:] = 0
        return {"out": 0}
    registry.register(Definition("mutator", {"signal": Port("recording")},
                                  {"out": Port("json")}, mutate, lambda p: None), trusted=True)
    cache = Cache(max_bytes=100)
    executor = Executor(registry, cache=cache)
    result = executor.execute(Workflow((Node("demo", "simulate"),
                                       Node("mutator", "mutator", inputs={"signal": Connection("demo")}))))
    assert np.any(result.outputs["demo"]["out"].data_uv != 0)
    assert cache._bytes <= 100


def test_cooperative_deadline_does_not_emit_success_after_slow_node():
    # Trigger a deterministic deadline after validate/source enumeration; no sleeps.
    with pytest.raises((WorkflowError, NodeExecutionError), match="time limit"):
        Executor(builtin_registry(), limits=Limits(max_seconds=1e-12)).execute(example())


def test_csv_file_contract_and_source_cache_invalidation(tmp_path):
    csv = tmp_path / "input.csv"
    np.savetxt(csv, np.arange(50).reshape(50, 1), header="x", comments="")
    workflow = Workflow((Node("source", "csv", {"path": "input.csv", "sfreq": 100}),))
    with pytest.raises(NodeExecutionError, match="source_root"):
        Executor(builtin_registry()).execute(workflow)
    executor = Executor(builtin_registry(), source_root=tmp_path)
    first = executor.execute(workflow)
    np.savetxt(csv, (np.arange(50) * 2).reshape(50, 1), header="x", comments="")
    second = executor.execute(workflow)
    assert not second.manifest["nodes"][0]["cache_hit"]
    assert not np.array_equal(first.outputs["source"]["out"].data_uv, second.outputs["source"]["out"].data_uv)
    traversal = Workflow((Node("source", "csv", {"path": "../outside.csv", "sfreq": 100}),))
    with pytest.raises(NodeExecutionError, match="within source_root"):
        executor.execute(traversal)
    with pytest.raises(NodeExecutionError, match="before matrix allocation"):
        Executor(builtin_registry(), source_root=tmp_path, limits=Limits(max_signal_values=20)).execute(workflow)


def test_overflowed_psd_cannot_emit_success(tmp_path):
    csv = tmp_path / "overflow.csv"
    np.savetxt(csv, np.tile([1e200, -1e200], 50)[:, None], header="x", comments="")
    workflow = Workflow((Node("csv", "csv", {"path": csv.name, "sfreq": 100}),
                         Node("psd", "psd", {"window_s": 0.5}, {"signal": Connection("csv")})))
    with np.errstate(over="ignore", invalid="ignore"), pytest.raises(NodeExecutionError, match="finite nonnegative"):
        Executor(builtin_registry(), source_root=tmp_path).execute(workflow)


@pytest.mark.parametrize("text,diagnosis", [("A\n1,2\n", "row width"), ("A,B\n1\n", "row width"),
                                            ("A,A\n1,2\n", "unique nonempty"), (",B\n1,2\n", "unique nonempty")])
def test_csv_preflight_rejects_implicit_indices_and_ambiguous_headers(tmp_path, text, diagnosis):
    (tmp_path / "invalid.csv").write_text(text)
    workflow = Workflow((Node("source", "csv", {"path": "invalid.csv", "sfreq": 100}),))
    with pytest.raises(NodeExecutionError, match=diagnosis):
        Executor(builtin_registry(), source_root=tmp_path).execute(workflow)


def test_cli_output_never_overwrites_existing_reports(tmp_path, capsys):
    output = tmp_path / "result"
    assert main(["validate", str(TEMPLATE)]) == 0
    assert main(["run", str(TEMPLATE), "--output", str(output)]) == 0
    manifest = (output / "manifest.json").read_bytes()
    assert (output / "summary-out.json").is_file()
    assert main(["run", str(TEMPLATE), "--output", str(output)]) == 2
    assert (output / "manifest.json").read_bytes() == manifest


def test_editor_renders_and_executes_real_workflow():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(ROOT / "studio_app.py"), default_timeout=60).run()
    assert not app.exception
    next(button for button in app.button if button.label == "Run workflow").click().run()
    assert not app.exception
    result = app.session_state["studio_result"]
    assert result.outputs["summary"]["out"]["n_samples"] == 2500


def test_engine_signal_filter_resample_and_cache_preserve_metadata():
    pytest.importorskip("biosignal_lab.engine")
    workflow = Workflow.from_json((ROOT / "examples/workflows/engine_filter.json").read_text())
    executor = Executor(builtin_registry())
    first = executor.execute(workflow)
    metadata = first.outputs["provenance"]["out"]
    assert metadata["sfreq"] == 125 and metadata["unit"] == "uV"
    assert [item["operation"] for item in metadata["history"]] == ["filter", "resample_poly"]
    second = executor.execute(workflow)
    assert all(node["cache_hit"] for node in second.manifest["nodes"])
    assert first.manifest["nodes"][-1]["output_sha256"] == second.manifest["nodes"][-1]["output_sha256"]
