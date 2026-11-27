"""Actual acquisition/AI integration; no hardware or physiological accuracy claim."""
from pathlib import Path

import numpy as np
import pytest

from biosignal_lab.studio import Workflow, Node, Connection, Executor, builtin_registry, Limits, NodeExecutionError

ROOT = Path(__file__).resolve().parents[2]


def research_executor():
    pytest.importorskip("biosignal_lab.live")
    pytest.importorskip("biosignal_lab.ai")
    pytest.importorskip("sklearn")
    return Executor(builtin_registry())


def test_simulated_acquisition_executes_actual_blocks_and_original_pipeline():
    executor = research_executor()
    workflow = Workflow.from_json((ROOT / "examples/workflows/live_to_report.json").read_text())
    first = executor.execute(workflow)
    second = executor.execute(workflow)
    diagnostics = first.outputs["acquisition"]["diagnostics"]
    assert diagnostics["samples"] == 1000 and diagnostics["blocks"] == 20
    assert diagnostics["clock"] == "simulated_device"
    assert diagnostics["final"]["dropped_samples"] == 0
    assert diagnostics["max_processing_seconds"] >= 0
    assert first.outputs["summary"]["out"]["n_samples"] == 1000
    np.testing.assert_array_equal(first.outputs["acquisition"]["signal"].data_uv,
                                  second.outputs["acquisition"]["signal"].data_uv)
    assert not second.manifest["nodes"][0]["cache_hit"]
    assert second.manifest["nodes"][1]["cache_hit"]


def test_subject_disjoint_evaluation_and_portable_inference_execute_real_models():
    executor = research_executor()
    workflow = Workflow.from_json((ROOT / "examples/workflows/grouped_ai.json").read_text())
    first = executor.execute(workflow)
    evaluation = first.outputs["evaluation"]["out"]
    assert evaluation["n_subjects"] == 4 and evaluation["n_samples"] == 32
    assert len(evaluation["folds"]) == 4
    assert all(not set(fold["train_subjects"]) & set(fold["test_subjects"]) for fold in evaluation["folds"])
    assert 0 <= evaluation["metrics"]["accuracy"] <= 1
    assert first.outputs["portable_model"]["out"]["format"] == "biosignal-linear-json"
    predictions = first.outputs["fitted_predictions"]["out"]
    assert len(predictions["predictions"]) == 32
    np.testing.assert_allclose(np.sum(predictions["probabilities"], axis=1), 1)
    second = executor.execute(workflow)
    assert second.manifest["nodes"][0]["cache_hit"]
    assert second.manifest["nodes"][2]["cache_hit"]
    assert not second.manifest["nodes"][1]["cache_hit"]
    assert first.outputs["fitted_predictions"]["out"] == second.outputs["fitted_predictions"]["out"]


def test_acquisition_and_epoch_resource_bounds_reject_before_allocation():
    executor = research_executor()
    executor.limits = Limits(max_signal_values=50)
    with pytest.raises(NodeExecutionError, match="before allocation"):
        executor.execute(Workflow((Node("live", "live_simulate"),)))
    with pytest.raises(NodeExecutionError, match="before allocation"):
        executor.execute(Workflow((Node("dataset", "ai_demo"),)))
    with pytest.raises(NodeExecutionError, match="4096 blocks"):
        Executor(builtin_registry()).execute(Workflow((Node("live", "live_simulate",
                                                          {"duration_s": 60, "sfreq": 4000, "n_channels": 1, "chunk_samples": 1}),)))


def test_explicit_epoch_labels_and_subject_identity_are_preserved():
    executor = research_executor()
    events = [{"sample": start, "label": label, "subject": subject}
              for start, label, subject in [(0, "task", "A"), (500, "rest", "A"),
                                            (1000, "task", "B"), (1500, "rest", "B")]]
    workflow = Workflow((Node("signal", "simulate", {"duration_s": 10, "n_channels": 1}),
                         Node("features", "epoch_features", {"duration_s": 2, "events": events},
                              {"signal": Connection("signal")})))
    dataset = executor.execute(workflow).outputs["features"]["out"]
    assert dataset.X.shape[0] == 4
    assert dataset.subjects.tolist() == ["A", "A", "B", "B"]
    assert dataset.provenance["events"] == events and dataset.provenance["unit"] == "uV"
    bad_events = [{"sample": 0, "label": "task", "subject": "A"},
                  {"sample": 250, "label": "rest", "subject": "B"}]
    with pytest.raises(NodeExecutionError, match="Overlapping samples"):
        executor.execute(Workflow((workflow.nodes[0], Node("bad", "epoch_features",
                                                         {"duration_s": 2, "events": bad_events},
                                                         {"signal": Connection("signal")}))))
