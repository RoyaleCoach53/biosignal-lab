"""Local scientific workflow builder. Start: streamlit run studio_app.py."""
from __future__ import annotations

from dataclasses import asdict
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from biosignal_lab.models import Recording, AnalysisResults
from biosignal_lab.studio import Workflow, Executor, Cache, builtin_registry
from biosignal_lab.studio.editor import frontend_available, render_editor


st.set_page_config(page_title="BioSignal Studio", page_icon="🧬", layout="wide")
st.title("BioSignal Studio")
st.caption("Build and reproduce local scientific workflows. Research and education only.")
st.markdown("Connect real processing nodes, inspect intermediate results, and download the workflow and execution manifest.")

registry = builtin_registry()
if "studio_workflow" not in st.session_state:
    template = Path(__file__).parent / "examples/workflows/eeg_quality.json"
    st.session_state.studio_workflow = Workflow.from_json(template.read_text()).to_dict()
    st.session_state.studio_positions = {}
    st.session_state.studio_undo = []
    st.session_state.studio_redo = []
    st.session_state.studio_cache = Cache()


def set_graph(value, *, history=True):
    workflow = Workflow.from_dict(value)
    if history:
        st.session_state.studio_undo = (st.session_state.studio_undo + [st.session_state.studio_workflow])[-30:]
        st.session_state.studio_redo = []
    st.session_state.studio_workflow = workflow.to_dict()
    st.session_state.pop("studio_result", None)


workflow = Workflow.from_dict(st.session_state.studio_workflow)
source_root = os.environ.get("BIOSIGNAL_STUDIO_SOURCE_ROOT")
executor = Executor(registry, cache=st.session_state.studio_cache,
                    source_root=Path(source_root) if source_root else None)
errors = []
try:
    executor.validate(workflow)
except ValueError as exc:
    errors.append(str(exc))

controls = st.columns(4)
if controls[0].button("Undo", disabled=not st.session_state.studio_undo):
    st.session_state.studio_redo.append(st.session_state.studio_workflow)
    previous = st.session_state.studio_undo.pop()
    set_graph(previous, history=False)
    st.rerun()
if controls[1].button("Redo", disabled=not st.session_state.studio_redo):
    st.session_state.studio_undo.append(st.session_state.studio_workflow)
    following = st.session_state.studio_redo.pop()
    set_graph(following, history=False)
    st.rerun()
controls[2].download_button("Download workflow", workflow.to_json(), "workflow.json", "application/json")
controls[3].download_button("Download Python runner", workflow.python_source(), "reproduce_workflow.py", "text/x-python")

if frontend_available():
    catalog = {name: {"inputs": {p: asdict(v) for p, v in definition.inputs.items()},
                      "outputs": {p: asdict(v) for p, v in definition.outputs.items()},
                      "description": definition.description}
               for name, definition in registry.definitions.items()}
    event = render_editor(workflow=workflow.to_dict(), catalog=catalog,
                   positions=st.session_state.studio_positions,
                   graph_digest=workflow.digest, errors=errors,
                   event_ack=st.session_state.get("studio_editor_event"),
                   key="scientific_graph_editor", default=None)
    if isinstance(event, dict) and event.get("event_id") != st.session_state.get("studio_editor_event"):
        st.session_state.studio_editor_event = event.get("event_id")
        if event.get("graph_digest") == workflow.digest:
            try:
                candidate = Workflow.from_json(json.dumps(event["workflow"]))
                if candidate.digest != workflow.digest:
                    set_graph(candidate.to_dict())
                positions = event.get("positions", {})
                if isinstance(positions, dict) and len(json.dumps(positions)) < 100_000:
                    valid_positions = {}
                    for key, position in positions.items():
                        if key not in {n.id for n in candidate.nodes} or not isinstance(position, dict):
                            continue
                        if all(isinstance(position.get(axis), (float, int)) and math.isfinite(position[axis]) for axis in ("x", "y")):
                            valid_positions[key] = {axis: float(position[axis]) for axis in ("x", "y")}
                    st.session_state.studio_positions = valid_positions
                st.session_state.pop("studio_editor_error", None)
            except (ValueError, TypeError, KeyError) as exc:
                st.session_state.studio_editor_error = f"Editor draft rejected: {exc}"
        st.rerun()  # Acknowledge accepted and rejected events to the component queue.
else:
    dot = ["digraph workflow { rankdir=LR;"]
    for node in workflow.nodes:
        dot.append(f'"{node.id}" [label="{node.id}\\n{node.kind}"];')
        for port, source in node.inputs.items():
            dot.append(f'"{source.node}" -> "{node.id}" [label="{port}"];')
    st.graphviz_chart("\n".join(dot) + "\n}")
if st.session_state.get("studio_editor_error"):
    st.error(st.session_state.studio_editor_error)

with st.expander("Keyboard-accessible node and connection editor"):
    kind = st.selectbox("Node operation", list(registry.definitions))
    definition = registry[kind]
    st.caption(definition.description)
    with st.form("add_node"):
        node_id = st.text_input("New node ID", value=f"node{len(workflow.nodes) + 1}")
        parameters = st.text_area("New node parameters (JSON object)", value="{}")
        selected = {}
        for port, contract in definition.inputs.items():
            choices = [f"{n.id}.{p}" for n in workflow.nodes if n.kind in registry.definitions
                       for p, provided in registry[n.kind].outputs.items() if provided.kind == contract.kind]
            selected[port] = st.selectbox(f"Source for {port} ({contract.kind})", [""] + choices)
        if st.form_submit_button("Add node"):
            try:
                parsed = json.loads(parameters)
                inputs = {port: {"node": value.split(".")[0], "port": value.split(".")[1]}
                          for port, value in selected.items() if value}
                set_graph({**workflow.to_dict(), "nodes": workflow.to_dict()["nodes"] + [
                    {"id": node_id, "kind": kind, "parameters": parsed, "inputs": inputs}]})
                st.rerun()
            except (ValueError, TypeError) as exc:
                st.error(str(exc))
    chosen = st.selectbox("Existing node", [n.id for n in workflow.nodes])
    current = next(n for n in workflow.nodes if n.id == chosen)
    with st.form("edit_node"):
        edited = st.text_area("Node definition (JSON)", json.dumps(next(n for n in workflow.to_dict()["nodes"] if n["id"] == chosen), indent=2))
        if st.form_submit_button("Apply node changes"):
            try:
                replacement = json.loads(edited)
                set_graph({**workflow.to_dict(), "nodes": [replacement if n["id"] == chosen else n for n in workflow.to_dict()["nodes"]]})
                st.rerun()
            except (ValueError, TypeError) as exc:
                st.error(str(exc))

with st.expander("Import workflow JSON"):
    with st.form("import_workflow"):
        imported = st.text_area("Workflow JSON", value="", height=180)
        if st.form_submit_button("Import draft"):
            try:
                set_graph(Workflow.from_json(imported).to_dict())
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    st.caption("Import accepts data only. Nodes execute only when you press Run workflow. File sources require a server-admin configured BIOSIGNAL_STUDIO_SOURCE_ROOT.")

for error in errors:
    st.error(error)
if st.button("Run workflow", type="primary", disabled=bool(errors)):
    with st.status("Executing scientific workflow", expanded=True) as status:
        try:
            result = executor.execute(workflow, progress=lambda node, state: status.write(f"{node}: {state}"))
            st.session_state.studio_result = result
            status.update(label=f"Completed {len(result.manifest['nodes'])} nodes", state="complete")
        except Exception as exc:
            status.update(label="Workflow failed", state="error")
            st.error(str(exc))

if "studio_result" in st.session_state:
    result = st.session_state.studio_result
    st.subheader("Execution results")
    st.download_button("Download execution manifest", result.manifest_json(), "execution-manifest.json", "application/json")
    node_id = st.selectbox("Inspect node output", list(result.outputs))
    for port, value in result.outputs[node_id].items():
        st.markdown(f"**{port}**")
        if isinstance(value, Recording):
            st.write(f"{len(value.channels)} channels · {value.sfreq:g} Hz · {value.duration_s:g} seconds · µV")
            count = min(value.data_uv.shape[1], 5000)
            st.line_chart(pd.DataFrame(value.data_uv[:, :count].T, columns=value.channels,
                                       index=np.arange(count) / value.sfreq))
            if count < value.data_uv.shape[1]:
                st.caption("Preview shows first 5,000 samples; execution uses the complete recording.")
        elif isinstance(value, AnalysisResults):
            st.json(value.summary())
        elif isinstance(value, dict) and "frequencies" in value and "power" in value:
            st.line_chart(pd.DataFrame(value["power"].T, index=value["frequencies"], columns=value["channels"]))
            st.caption(f"Frequency (Hz); power spectral density ({value['unit']})")
        elif isinstance(value, str):
            st.download_button("Download HTML report", value, f"{node_id}-{port}.html", "text/html")
            st.caption("HTML is downloaded rather than embedded in the editor.")
        elif hasattr(value, "data") and hasattr(value, "sfreq"):
            st.write({"channels": value.channels, "sfreq": value.sfreq, "unit": value.unit,
                      "modality": value.modality, "reference": value.reference, "history": value.history})
        elif hasattr(value, "X") and hasattr(value, "subjects"):
            st.write({"samples": value.X.shape[0], "features": value.X.shape[1],
                      "subjects": len(np.unique(value.subjects)), "feature_names": value.feature_names,
                      "provenance": value.provenance})
            st.dataframe(pd.DataFrame(value.X, columns=value.feature_names))
        elif hasattr(value, "to_dict"):
            st.json(value.to_dict())
        else:
            st.json(value)
