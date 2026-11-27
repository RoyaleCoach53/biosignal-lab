"""Importable component wrapper; also works when Streamlit executes st.Page files."""
from pathlib import Path


def frontend_available() -> bool:
    return (Path(__file__).parent / "editor_frontend" / "index.html").is_file()


def render_editor(**arguments):
    # declare_component inspects its caller's module. Keep this call in a real
    # imported module rather than a page script executed by st.Page/navigation.
    import streamlit.components.v1 as components
    editor = components.declare_component("biosignal_studio_editor",
                                           path=str(Path(__file__).parent / "editor_frontend"))
    return editor(**arguments)
