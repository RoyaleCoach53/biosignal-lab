from pathlib import Path

import pytest


def test_unified_navigation_reaches_functional_pages():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / "platform_app.py"), default_timeout=60).run()
    assert not app.exception
    for page in ("engine_app.py", "live_app.py", "ai_app.py", "studio_app.py", "workspace_app.py", "app.py"):
        app.switch_page(page).run()
        assert not app.exception, page
        assert len(app.title) >= 1, page


def test_unified_cli_executes_and_preserves_workflow_reports(tmp_path, capsys):
    from biosignal_lab.cli import main

    root = Path(__file__).resolve().parents[1]
    source = str(root / "examples/workflows/engine_filter.json")
    destination = tmp_path / "experiment"
    assert main(["workflow", "validate", source]) == 0
    assert main(["workflow", "run", source, "--output", str(destination)]) == 0
    manifest = (destination / "manifest.json").read_bytes()
    assert main(["workflow", "run", source, "--output", str(destination)]) == 2
    assert (destination / "manifest.json").read_bytes() == manifest
    assert '"nodes_executed": 6' in capsys.readouterr().out
