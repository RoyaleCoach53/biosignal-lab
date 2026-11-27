"""Bounded, cooperative DAG execution with explicit trusted node registration."""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
import copy
from dataclasses import dataclass, fields, is_dataclass
import hashlib
import inspect
from importlib.metadata import version, PackageNotFoundError
import json
from pathlib import Path
import threading
import time
from typing import Callable, Any

import numpy as np

from .model import Workflow, canonical
from ..models import Recording, AnalysisResults


class WorkflowError(ValueError):
    """Invalid graph or a scientific contract violation."""


class ExecutionCancelled(RuntimeError):
    """Cancellation was observed between nodes."""


class NodeExecutionError(RuntimeError):
    def __init__(self, node_id, cause):
        self.node_id = node_id
        self.cause = cause
        super().__init__(f"Node {node_id}: {type(cause).__name__}: {cause}")


@dataclass(frozen=True)
class Port:
    kind: str
    unit: str | None = None
    sfreq: float | None = None
    modality: str | None = None


@dataclass(frozen=True)
class Definition:
    kind: str
    inputs: dict[str, Port]
    outputs: dict[str, Port]
    run: Callable
    validate: Callable[[dict], None]
    revision: str = "1"
    pure: bool = True
    description: str = ""


class Registry:
    """Only caller-supplied Python code can register nodes; no entry-point loading."""

    def __init__(self):
        self.definitions = {}

    def register(self, definition: Definition, *, trusted: bool = False):
        if not trusted:
            raise PermissionError("Node plugins run Python code; explicitly pass trusted=True after review")
        if definition.kind in self.definitions:
            raise ValueError(f"Node kind already registered: {definition.kind}")
        if not definition.outputs or not callable(definition.run) or not callable(definition.validate):
            raise ValueError("Node definition requires outputs, run, and validate")
        self.definitions[definition.kind] = definition

    def __getitem__(self, kind):
        try:
            return self.definitions[kind]
        except KeyError:
            raise WorkflowError(f"Unregistered node kind: {kind}") from None


@dataclass(frozen=True)
class Limits:
    max_nodes: int = 64
    max_signal_values: int = 4_000_000
    max_output_bytes: int = 128_000_000
    max_seconds: float = 60.0
    max_source_bytes: int = 32_000_000

    def __post_init__(self):
        for item in fields(self):
            value = getattr(self, item.name)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not np.isfinite(value) or value <= 0:
                raise ValueError(f"{item.name} must be finite and positive")


@dataclass
class Context:
    limits: Limits
    cancel: threading.Event
    source_root: Path | None = None

    def resolve_source(self, name: str) -> Path:
        if self.source_root is None:
            raise PermissionError("File sources require an explicitly configured source_root")
        root = self.source_root.resolve()
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise PermissionError("Source must be an existing regular file within source_root")
        if path.stat().st_size > self.limits.max_source_bytes:
            raise WorkflowError("Source exceeds configured byte limit")
        return path


def _hash_value(hasher, value):
    def frame(payload):
        hasher.update(len(payload).to_bytes(8, "big"))
        hasher.update(payload)
    if isinstance(value, np.ndarray):
        if value.dtype.hasobject:
            raise TypeError("Object arrays are not workflow data")
        frame(canonical(["array", value.dtype.str, list(value.shape)]).encode())
        frame(np.ascontiguousarray(value).tobytes())
    elif is_dataclass(value):
        frame(canonical(["dataclass", type(value).__module__, type(value).__qualname__, len(fields(value))]).encode())
        for item in fields(value):
            frame(item.name.encode())
            frame(bytes.fromhex(fingerprint(getattr(value, item.name))))
    elif isinstance(value, Mapping):
        frame(canonical(["mapping", len(value)]).encode())
        for key in sorted(value):
            frame(canonical(key).encode())
            frame(bytes.fromhex(fingerprint(value[key])))
    elif isinstance(value, (list, tuple)):
        frame(canonical([type(value).__name__, len(value)]).encode())
        for item in value:
            frame(bytes.fromhex(fingerprint(item)))
    elif isinstance(value, np.generic):
        _hash_value(hasher, value.item())
    else:
        frame(canonical([type(value).__name__, value]).encode())


def fingerprint(value) -> str:
    hasher = hashlib.sha256()
    _hash_value(hasher, value)
    return hasher.hexdigest()


def source_fingerprint() -> str:
    """Bind editable development runs to installed Python source, not just version."""
    root = Path(__file__).resolve().parents[1]
    hasher = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        hasher.update(str(path.relative_to(root)).encode())
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def definition_fingerprint(definition):
    try:
        source = inspect.getsourcefile(definition.run)
    except TypeError:
        source = None
    if source and Path(source).is_file():
        try:
            function_source = inspect.getsource(definition.run)
        except (OSError, TypeError):
            function_source = ""
        return fingerprint({"file_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                            "callable": getattr(definition.run, "__qualname__", type(definition.run).__qualname__),
                            "function_source": function_source, "revision": definition.revision})
    # Explicit revision is the trust contract for opaque, reviewed extensions.
    return fingerprint({"kind": definition.kind, "revision": definition.revision})


def data_bytes(value) -> int:
    if isinstance(value, np.ndarray):
        return value.nbytes
    if is_dataclass(value):
        return sum(data_bytes(getattr(value, f.name)) for f in fields(value))
    if isinstance(value, Mapping):
        return sum(len(str(k).encode()) + data_bytes(v) for k, v in value.items())
    if isinstance(value, (tuple, list)):
        return sum(data_bytes(v) for v in value)
    return len(str(value).encode())


def detached(value):
    """Copy typed values, including immutable engine signals with mapping proxies."""
    if isinstance(value, np.ndarray):
        return value.copy()
    if is_dataclass(value):
        return type(value)(**{f.name: detached(getattr(value, f.name)) for f in fields(value) if f.init})
    if isinstance(value, Mapping):
        return {k: detached(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return tuple(detached(v) for v in value)
    if isinstance(value, list):
        return [detached(v) for v in value]
    return copy.deepcopy(value)


def _port_check(value, port: Port):
    kind = port.kind
    if kind == "recording":
        if not isinstance(value, Recording):
            raise WorkflowError("Expected Recording")
        unit, sfreq, modality = "uV", value.sfreq, value.modality
    elif kind == "analysis":
        if not isinstance(value, AnalysisResults):
            raise WorkflowError("Expected AnalysisResults")
        unit, sfreq, modality = "uV", value.recording.sfreq, value.recording.modality
    elif kind == "signal":
        from ..engine import Signal
        if not isinstance(value, Signal):
            raise WorkflowError("Expected engine Signal")
        unit, sfreq, modality = value.unit, value.sfreq, value.modality
    elif kind == "dataset":
        from ..ai import FeatureDataset
        if not isinstance(value, FeatureDataset):
            raise WorkflowError("Expected validated FeatureDataset")
        unit = sfreq = modality = None
    elif kind == "linear_model":
        from ..ai import LinearModel
        if not isinstance(value, LinearModel):
            raise WorkflowError("Expected validated portable LinearModel")
        unit = sfreq = modality = None
    elif kind == "spectrum":
        if not isinstance(value, dict) or not {"frequencies", "power", "unit", "sfreq", "channels"} <= set(value):
            raise WorkflowError("Expected spectrum")
        f, p = value["frequencies"], value["power"]
        if not isinstance(f, np.ndarray) or not isinstance(p, np.ndarray) or f.ndim != 1 or p.ndim != 2 or p.shape[1] != len(f):
            raise WorkflowError("Invalid spectrum dimensions")
        unit, sfreq, modality = value["unit"], value["sfreq"], value.get("modality")
        if (f.dtype.kind not in "fiu" or p.dtype.kind not in "fiu" or len(f) < 2 or p.shape[0] < 1
                or not np.all(np.isfinite(f)) or not np.all(np.isfinite(p))
                or np.any(f < 0) or np.any(np.diff(f) <= 0) or np.any(p < 0)):
            raise WorkflowError("Spectrum requires finite nonnegative real powers and increasing nonnegative frequencies")
        if isinstance(sfreq, bool) or not isinstance(sfreq, (int, float)) or not np.isfinite(sfreq) or sfreq <= 0 or f[-1] > sfreq / 2 * (1 + 1e-12):
            raise WorkflowError("Spectrum requires positive sampling rate and frequencies within Nyquist")
        channels = value["channels"]
        if (not isinstance(channels, (tuple, list)) or len(channels) != p.shape[0]
                or any(not isinstance(label, str) or not label for label in channels)
                or len(set(channels)) != len(channels) or not isinstance(unit, str) or not unit):
            raise WorkflowError("Spectrum requires explicit units and unique matching channel labels")
    elif kind == "json":
        canonical(value)
        unit = sfreq = modality = None
    elif kind == "html":
        if not isinstance(value, str):
            raise WorkflowError("Expected HTML text")
        unit = sfreq = modality = None
    else:
        raise WorkflowError(f"Unknown port data type: {kind}")
    if port.unit is not None and port.unit != unit:
        raise WorkflowError(f"Unit mismatch: expected {port.unit}, received {unit}")
    if port.sfreq is not None and not np.isclose(port.sfreq, sfreq, rtol=1e-10, atol=0):
        raise WorkflowError(f"Sampling rate mismatch: expected {port.sfreq}, received {sfreq}")
    if port.modality is not None and port.modality != modality:
        raise WorkflowError(f"Modality mismatch: expected {port.modality}, received {modality}")


class Cache:
    """Bounded in-memory LRU; copies prevent later mutation corrupting cached data."""

    def __init__(self, max_bytes=32_000_000):
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("Cache max_bytes must be a positive integer")
        self.max_bytes = max_bytes
        self._entries = OrderedDict()
        self._bytes = 0

    def get(self, key):
        if key not in self._entries:
            return None
        self._entries.move_to_end(key)
        return detached(self._entries[key][0])

    def put(self, key, value):
        size = data_bytes(value)
        if size > self.max_bytes:
            return
        if key in self._entries:
            self._bytes -= self._entries.pop(key)[1]
        while self._entries and self._bytes + size > self.max_bytes:
            self._bytes -= self._entries.popitem(last=False)[1][1]
        self._entries[key] = (detached(value), size)
        self._bytes += size


@dataclass
class ExecutionResult:
    outputs: dict[str, dict]
    manifest: dict

    def manifest_json(self):
        return json.dumps(self.manifest, indent=2, allow_nan=False)


class Executor:
    def __init__(self, registry: Registry, *, limits: Limits | None = None,
                 cache: Cache | None = None, source_root: Path | None = None):
        self.registry = registry
        self.limits = limits or Limits()
        self.cache = cache or Cache()
        self.source_root = source_root

    def validate(self, workflow: Workflow) -> list:
        if len(workflow.nodes) > self.limits.max_nodes:
            raise WorkflowError("Workflow exceeds node limit")
        nodes = {n.id: n for n in workflow.nodes}
        for node in workflow.nodes:
            definition = self.registry[node.kind]
            try:
                definition.validate(node.parameters)
            except (ValueError, TypeError) as exc:
                raise WorkflowError(f"Node {node.id}: {exc}") from exc
            if set(node.inputs) != set(definition.inputs):
                raise WorkflowError(f"Node {node.id} needs input ports {sorted(definition.inputs)}")
            for port, link in node.inputs.items():
                if link.node not in nodes:
                    raise WorkflowError(f"Node {node.id}: missing upstream node {link.node}")
                source = self.registry[nodes[link.node].kind]
                if link.port not in source.outputs:
                    raise WorkflowError(f"Node {node.id}: missing output port {link.port}")
                provided, required = source.outputs[link.port], definition.inputs[port]
                if provided.kind != required.kind:
                    raise WorkflowError(f"Node {node.id}: {provided.kind} cannot connect to {required.kind}")
                for attribute in ("unit", "sfreq", "modality"):
                    actual, expected = getattr(provided, attribute), getattr(required, attribute)
                    if actual is not None and expected is not None and actual != expected:
                        raise WorkflowError(f"Node {node.id}: incompatible {attribute}")
        order, visited, active = [], set(), set()
        def visit(node_id):
            if node_id in active:
                raise WorkflowError(f"Cycle detected at node {node_id}")
            if node_id in visited:
                return
            active.add(node_id)
            for connection in nodes[node_id].inputs.values():
                visit(connection.node)
            active.remove(node_id)
            visited.add(node_id)
            order.append(nodes[node_id])
        for node in workflow.nodes:
            visit(node.id)
        return order

    def execute(self, workflow: Workflow, *, cancel: threading.Event | None = None,
                progress: Callable[[str, str], Any] | None = None) -> ExecutionResult:
        # Snapshot mutable parameter objects so callbacks cannot change the graph.
        workflow = Workflow.from_json(workflow.to_json())
        order = self.validate(workflow)
        context = Context(self.limits, cancel or threading.Event(), self.source_root)
        started = time.perf_counter()
        outputs, records = {}, []
        used_bytes = 0
        dependencies = {}
        source_hash = source_fingerprint()
        for package in ("biosignal-lab", "numpy", "scipy", "pandas", "mne", "scikit-learn", "PyWavelets"):
            try:
                dependencies[package] = version(package)
            except PackageNotFoundError:
                pass
        for node in order:
            if context.cancel.is_set():
                raise ExecutionCancelled("Workflow cancelled between nodes")
            if time.perf_counter() - started > self.limits.max_seconds:
                raise WorkflowError("Workflow exceeded cooperative time limit")
            definition = self.registry[node.kind]
            inputs = {port: outputs[link.node][link.port] for port, link in node.inputs.items()}
            tick = time.perf_counter()
            if progress:
                progress(node.id, "running")
            try:
                for port, value in inputs.items():
                    _port_check(value, definition.inputs[port])
                key = fingerprint({"kind": node.kind, "revision": definition.revision,
                                   "parameters": node.parameters, "inputs": inputs,
                                   "dependencies": dependencies, "source_sha256": source_hash,
                                   "definition_sha256": definition_fingerprint(definition)})
                value = self.cache.get(key) if definition.pure else None
                cached = value is not None
                if not cached:
                    # Nodes receive detached values: mutations cannot corrupt upstream outputs.
                    value = definition.run(detached(inputs), detached(node.parameters), context)
                if not isinstance(value, dict) or set(value) != set(definition.outputs):
                    raise WorkflowError("Node returned incorrect output ports")
                for port, item in value.items():
                    _port_check(item, definition.outputs[port])
                    if isinstance(item, Recording) and item.data_uv.size > self.limits.max_signal_values:
                        raise WorkflowError("Signal exceeds configured sample-value limit")
                    if definition.outputs[port].kind == "signal" and item.data.size > self.limits.max_signal_values:
                        raise WorkflowError("Signal exceeds configured sample-value limit")
                    if definition.outputs[port].kind == "dataset" and item.X.size > self.limits.max_signal_values:
                        raise WorkflowError("Feature dataset exceeds configured value limit")
                used_bytes += data_bytes(value)
                if used_bytes > self.limits.max_output_bytes:
                    raise WorkflowError("Workflow exceeds retained-output byte limit")
                if context.cancel.is_set():
                    raise ExecutionCancelled("Workflow cancelled after current node")
                if time.perf_counter() - started > self.limits.max_seconds:
                    raise WorkflowError("Workflow exceeded cooperative time limit")
                if definition.pure and not cached:
                    self.cache.put(key, value)
                outputs[node.id] = value
                records.append({"node": node.id, "kind": node.kind, "revision": definition.revision,
                                "input_sha256": fingerprint(inputs), "output_sha256": fingerprint(value),
                                "cache_hit": cached, "seconds": time.perf_counter() - tick})
                if progress:
                    progress(node.id, "cached" if cached else "completed")
            except ExecutionCancelled:
                raise
            except Exception as exc:
                if progress:
                    progress(node.id, "failed")
                raise NodeExecutionError(node.id, exc) from exc
        return ExecutionResult(outputs, {"schema_version": 1, "workflow": workflow.to_dict(),
                               "workflow_sha256": workflow.digest, "dependencies": dependencies,
                               "source_sha256": source_hash,
                               "nodes": records, "retained_output_bytes": used_bytes,
                               "seconds": time.perf_counter() - started,
                               "scope": "Local scientific execution; no clinical validation; no raw data embedded."})
