"""Importable component wrapper; also works when Streamlit executes st.Page files."""
from pathlib import Path
import math

from .model import IDENTIFIER


def clean_view_state(workflow, positions=None, groups=None):
    """Bound untrusted canvas metadata without changing scientific workflow JSON."""
    ids = {node.id for node in workflow.nodes}
    valid_positions = {}
    for key, value in (positions.items() if isinstance(positions, dict) else []):
        if key not in ids or not isinstance(value, dict):
            continue
        if all(isinstance(value.get(axis), (float, int)) and not isinstance(value[axis], bool)
               and math.isfinite(value[axis]) and abs(value[axis]) <= 10_000_000 for axis in ("x", "y")):
            valid_positions[key] = {axis: float(value[axis]) for axis in ("x", "y")}
    valid_groups, assigned, seen_ids = [], set(), set()
    for group in (groups[:128] if isinstance(groups, list) else []):
        if not isinstance(group, dict) or set(group) != {"id", "name", "nodes"}:
            continue
        group_id, name, nodes = group["id"], group["name"], group["nodes"]
        if (not isinstance(group_id, str) or not IDENTIFIER.fullmatch(group_id) or group_id in seen_ids
                or not isinstance(name, str) or not 1 <= len(name) <= 100 or not isinstance(nodes, list)):
            continue
        members = []
        for node_id in nodes[:128]:
            if isinstance(node_id, str) and node_id in ids and node_id not in assigned:
                members.append(node_id)
                assigned.add(node_id)
        if members:
            valid_groups.append({"id": group_id, "name": name, "nodes": members})
            seen_ids.add(group_id)
    return valid_positions, valid_groups


def frontend_available() -> bool:
    return (Path(__file__).parent / "editor_frontend" / "index.html").is_file()


def render_editor(**arguments):
    # declare_component inspects its caller's module. Keep this call in a real
    # imported module rather than a page script executed by st.Page/navigation.
    import streamlit.components.v1 as components
    editor = components.declare_component("biosignal_studio_editor",
                                           path=str(Path(__file__).parent / "editor_frontend"))
    return editor(**arguments)
