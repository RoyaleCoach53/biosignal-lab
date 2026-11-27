"""Versioned, data-only workflow definitions. Importing a workflow executes no code."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any

IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class Connection:
    node: str
    port: str = "out"


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    parameters: dict = field(default_factory=dict)
    inputs: dict[str, Connection] = field(default_factory=dict)


@dataclass(frozen=True)
class Workflow:
    nodes: tuple[Node, ...]
    name: str = "Untitled experiment"
    schema_version: int = 1

    def __post_init__(self):
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("Unsupported workflow schema_version; expected 1")
        if not isinstance(self.name, str) or len(self.name) > 200:
            raise ValueError("Workflow name must be text of at most 200 characters")
        if not 1 <= len(self.nodes) <= 128:
            raise ValueError("Workflow must contain 1..128 nodes")
        ids = []
        for node in self.nodes:
            if not isinstance(node, Node):
                raise ValueError("Expected Node definitions")
            if not isinstance(node.id, str) or not IDENTIFIER.fullmatch(node.id):
                raise ValueError("Node IDs must be simple identifiers, at most 64 characters")
            if not isinstance(node.kind, str) or not IDENTIFIER.fullmatch(node.kind):
                raise ValueError(f"Invalid node kind for {node.id}")
            if not isinstance(node.parameters, dict) or not isinstance(node.inputs, dict):
                raise ValueError(f"Parameters and inputs must be objects for {node.id}")
            for port, connection in node.inputs.items():
                if not isinstance(port, str) or not IDENTIFIER.fullmatch(port):
                    raise ValueError(f"Invalid input port for {node.id}")
                if not isinstance(connection, Connection):
                    raise ValueError(f"Expected Connection for {node.id}.{port}")
                if not isinstance(connection.node, str) or not isinstance(connection.port, str):
                    raise ValueError("Connection identifiers must be text")
            canonical(node.parameters)  # Reject non-JSON objects, NaN, and infinity.
            ids.append(node.id)
        if len(set(ids)) != len(ids):
            raise ValueError("Node IDs must be unique")

    def to_dict(self) -> dict:
        return {"schema_version": self.schema_version, "name": self.name,
                "nodes": [{"id": n.id, "kind": n.kind, "parameters": n.parameters,
                           "inputs": {p: {"node": c.node, "port": c.port}
                                      for p, c in n.inputs.items()}} for n in self.nodes]}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, allow_nan=False)

    @property
    def digest(self) -> str:
        return hashlib.sha256(canonical(self.to_dict()).encode()).hexdigest()

    @classmethod
    def from_dict(cls, value: dict) -> Workflow:
        if not isinstance(value, dict) or set(value) - {"schema_version", "name", "nodes"}:
            raise ValueError("Unknown workflow fields")
        nodes = value.get("nodes")
        if not isinstance(nodes, list) or not 1 <= len(nodes) <= 128:
            raise ValueError("nodes must be a list containing 1..128 objects")
        parsed = []
        for node in nodes:
            if not isinstance(node, dict) or set(node) - {"id", "kind", "parameters", "inputs"}:
                raise ValueError("Unknown node fields")
            if not {"id", "kind"} <= set(node):
                raise ValueError("Every node needs id and kind")
            inputs = node.get("inputs", {})
            if not isinstance(inputs, dict):
                raise ValueError("Node inputs must be an object")
            connections = {}
            for port, connection in inputs.items():
                if not isinstance(connection, dict) or set(connection) - {"node", "port"} or "node" not in connection:
                    raise ValueError("Connection must contain node and optional port")
                connections[port] = Connection(connection["node"], connection.get("port", "out"))
            parsed.append(Node(node["id"], node["kind"], node.get("parameters", {}), connections))
        return cls(tuple(parsed), value.get("name", "Untitled experiment"), value.get("schema_version", 1))

    @classmethod
    def from_json(cls, text: str, *, max_bytes: int = 1_000_000) -> Workflow:
        if len(text.encode("utf-8")) > max_bytes:
            raise ValueError("Workflow exceeds import size limit")
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"Duplicate JSON field: {key}")
                result[key] = value
            return result
        try:
            return cls.from_dict(json.loads(text, object_pairs_hook=unique,
                                           parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"Invalid number {x}"))))
        except (json.JSONDecodeError, RecursionError, TypeError) as exc:
            raise ValueError("Invalid workflow JSON") from exc

    def python_source(self) -> str:
        """Generate a reproducible runner, never interpolate workflow text as code."""
        payload = repr(self.to_json())
        return ("from biosignal_lab.studio import Workflow, Executor, builtin_registry\n\n"
                f"workflow = Workflow.from_json({payload})\n"
                "result = Executor(builtin_registry()).execute(workflow)\n"
                "print(result.manifest_json())\n")
