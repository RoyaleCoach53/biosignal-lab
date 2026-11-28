"""Concurrency contracts with synchronization rather than timing-only speed claims."""
import threading

import pytest

from biosignal_lab.studio import (Registry, Definition, Port, Workflow, Node, Connection,
                                  Executor, Cache, Limits, builtin_registry, NodeExecutionError, WorkflowError)


def test_only_explicitly_reviewed_pure_nodes_overlap_and_callbacks_stay_on_owner():
    registry = Registry()
    barrier = threading.Barrier(2)
    worker_ids, callbacks = set(), []
    owner = threading.get_ident()
    def run(i, p, c):
        worker_ids.add(threading.get_ident())
        barrier.wait(timeout=3)
        return {"out": p["label"]}
    registry.register(Definition("parallel", {}, {"out": Port("json")}, run, lambda p: None,
                                  parallel_safe=True), trusted=True)
    workflow = Workflow((Node("a", "parallel", {"label": "A"}), Node("b", "parallel", {"label": "B"})))
    result = Executor(registry, max_workers=2).execute(workflow,
                                                     progress=lambda n, s: callbacks.append(threading.get_ident()))
    assert len(worker_ids) == 2 and owner not in worker_ids
    assert set(callbacks) == {owner}
    assert result.outputs["a"]["out"] == "A" and result.outputs["b"]["out"] == "B"
    assert [node["node"] for node in result.manifest["nodes"]] == ["a", "b"]


def test_unreviewed_plugins_and_impure_nodes_are_exclusive_serial_barriers():
    registry = Registry()
    calls = []
    owner = threading.get_ident()
    def run(i, p, c):
        calls.append((p["label"], threading.get_ident()))
        return {"out": p["label"]}
    registry.register(Definition("safe", {}, {"out": Port("json")}, run, lambda p: None,
                                  parallel_safe=True), trusted=True)
    registry.register(Definition("side_effect", {}, {"out": Port("json")}, run, lambda p: None,
                                  pure=False, parallel_safe=True), trusted=True)
    registry.register(Definition("unreviewed", {}, {"out": Port("json")}, run, lambda p: None), trusted=True)
    workflow = Workflow(tuple(Node(label, kind, {"label": label}) for label, kind in
                              [("a", "safe"), ("b", "side_effect"), ("c", "safe"), ("d", "unreviewed")]))
    Executor(registry, max_workers=4).execute(workflow)
    assert calls == [(label, owner) for label in ["a", "b", "c", "d"]]


def test_worker_failure_cancels_cooperative_peer_and_does_not_mutate_caller_event():
    registry = Registry()
    started, finished = threading.Event(), threading.Event()
    external = threading.Event()
    def peer(i, p, c):
        started.set()
        assert c.cancel.wait(timeout=3), "Sibling failure must wake a cooperative peer"
        finished.set()
        return {"out": "stopped"}
    def fail(i, p, c):
        assert started.wait(timeout=2)
        raise ValueError("intentional worker failure")
    for kind, run in [("peer", peer), ("fail", fail)]:
        registry.register(Definition(kind, {}, {"out": Port("json")}, run, lambda p: None,
                                      parallel_safe=True), trusted=True)
    with pytest.raises(NodeExecutionError, match="intentional worker failure"):
        Executor(registry, max_workers=2).execute(Workflow((Node("a", "peer"), Node("b", "fail"))), cancel=external)
    assert finished.is_set() and not external.is_set()


def test_parallel_deadline_signals_cooperative_peers_before_return():
    registry = Registry()
    finished = []
    def run(i, p, c):
        assert c.cancel.wait(timeout=3)
        finished.append(p["label"])
        return {"out": 1}
    registry.register(Definition("waiter", {}, {"out": Port("json")}, run, lambda p: None,
                                  parallel_safe=True), trusted=True)
    with pytest.raises(WorkflowError, match="time limit"):
        Executor(registry, max_workers=2, limits=Limits(max_seconds=.15)).execute(
            Workflow((Node("a", "waiter", {"label": "a"}), Node("b", "waiter", {"label": "b"}))))
    assert sorted(finished) == ["a", "b"]


def test_parallel_input_budget_serializes_copies_and_retained_output_budget_is_shared():
    registry = Registry()
    owner = threading.get_ident()
    calls = []
    registry.register(Definition("source", {}, {"out": Port("json")}, lambda i, p, c: {"out": "x" * 100},
                                  lambda p: None, parallel_safe=True), trusted=True)
    def run(i, p, c):
        calls.append(threading.get_ident())
        return {"out": i["value"]}
    registry.register(Definition("copy", {"value": Port("json")}, {"out": Port("json")},
                                  run, lambda p: None, parallel_safe=True), trusted=True)
    workflow = Workflow((Node("source", "source"), Node("a", "copy", {"tag": "a"}, inputs={"value": Connection("source")}),
                         Node("b", "copy", {"tag": "b"}, inputs={"value": Connection("source")})))
    Executor(registry, max_workers=4, limits=Limits(max_parallel_input_bytes=50)).execute(workflow)
    assert calls == [owner, owner]
    with pytest.raises(NodeExecutionError, match="retained-output"):
        Executor(registry, max_workers=4, limits=Limits(max_output_bytes=250)).execute(workflow)


def test_serial_and_parallel_scientific_output_hashes_and_manifest_order_match():
    workflow = Workflow((Node("a", "simulate", {"seed": 1}),
                         Node("a_analysis", "analyze", inputs={"signal": Connection("a")}),
                         Node("b", "simulate", {"seed": 2}),
                         Node("b_analysis", "analyze", inputs={"signal": Connection("b")})))
    serial = Executor(builtin_registry()).execute(workflow)
    parallel = Executor(builtin_registry(), max_workers=4).execute(workflow)
    assert [node["node"] for node in serial.manifest["nodes"]] == [node["node"] for node in parallel.manifest["nodes"]]
    assert [node["output_sha256"] for node in serial.manifest["nodes"]] == [node["output_sha256"] for node in parallel.manifest["nodes"]]
    assert not parallel.outputs["a"]["out"].data_uv.flags.writeable


def test_cache_ownership_prevents_reentrant_executions_and_is_released_after_error():
    cache = Cache()
    executor = Executor(builtin_registry(), cache=cache)
    workflow = Workflow((Node("demo", "simulate"),))
    def callback(node, state):
        if state == "running":
            with pytest.raises(RuntimeError, match="one active"):
                Executor(builtin_registry(), cache=cache).execute(workflow)
    executor.execute(workflow, progress=callback)
    assert executor.execute(workflow).manifest["nodes"][0]["cache_hit"]
    for workers in (0, 5, True, 1.5):
        with pytest.raises(ValueError, match="max_workers"):
            Executor(builtin_registry(), max_workers=workers)
