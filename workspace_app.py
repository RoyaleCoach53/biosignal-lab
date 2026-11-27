"""Explicit local project persistence and recovery; no automatic data uploads."""
import json
from pathlib import Path

import streamlit as st

from biosignal_lab.workspace import Workspace

st.set_page_config(page_title="BioSignal Projects", layout="wide")
st.title("Projects")
st.caption("Local project metadata and versioned JSON workflows. Raw recordings stay outside this store.")
root = st.text_input("Workspace directory", str(Path.cwd() / "local-results" / "projects"))
try:
    store = Workspace(root)
except (OSError, ValueError) as error:
    st.error(str(error))
    st.stop()

with st.form("new_project"):
    title = st.text_input("New project title", max_chars=200)
    if st.form_submit_button("Create project"):
        try:
            st.session_state["project_id"] = store.create_project(title)
            st.success("Project created")
        except (OSError, ValueError) as error:
            st.error(str(error))

projects = store.projects()
if projects:
    labels = {item["id"]: item["title"] for item in projects}
    selected = st.selectbox("Project", list(labels), format_func=labels.get)
    st.caption(f"Project identifier: {selected}")
    document = st.text_input("Document identifier", "workflow", max_chars=64)
    try:
        revisions = store.revisions(selected, document)
        if revisions:
            revision = st.selectbox("Saved revision", revisions, index=len(revisions) - 1)
            payload = store.load(selected, document, revision)
            st.json(payload)
            st.download_button("Export saved JSON", json.dumps(payload, indent=2, allow_nan=False),
                               file_name=f"{document}-{revision}.json", mime="application/json")
        source = st.text_area("JSON document to save", '{"schema_version": 1}', height=160)
        if st.button("Save new revision"):
            if len(source.encode("utf-8")) > store.max_document_bytes:
                raise ValueError("Document exceeds size limit")
            payload = json.loads(source)
            revision = store.save(selected, document, payload)
            st.success(f"Saved revision {revision}; previous revisions are preserved")
    except (OSError, ValueError) as error:
        st.error(str(error))
else:
    st.info("Create a project to save and recover workflow JSON between sessions.")
