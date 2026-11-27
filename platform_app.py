"""Unified local entrypoint: python -m streamlit run platform_app.py."""
import streamlit as st

pages = [
    st.Page("app.py", title="Signal Explorer", icon="📈", default=True),
    st.Page("engine_app.py", title="Scientific Engine", icon="🔬"),
    st.Page("live_app.py", title="Live Lab", icon="📡"),
    st.Page("ai_app.py", title="AI Lab", icon="🧮"),
    st.Page("studio_app.py", title="Studio", icon="🔗"),
    st.Page("workspace_app.py", title="Projects", icon="📁"),
]
st.navigation(pages).run()
