from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_project_ui_creates_saves_and_recovers_document(tmp_path):
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "workspace_app.py"),
                            default_timeout=30).run()
    assert not app.exception
    next(x for x in app.text_input if x.label == "Workspace directory").set_value(str(tmp_path)).run()
    next(x for x in app.text_input if x.label == "New project title").set_value("Synthetic study")
    next(x for x in app.button if x.label == "Create project").click().run()
    assert not app.exception
    assert next(x for x in app.selectbox if x.label == "Project").options == ["Synthetic study"]
    next(x for x in app.text_area if x.label == "JSON document to save").set_value('{"seed": 42}')
    next(x for x in app.button if x.label == "Save new revision").click().run()
    assert any("Saved revision 1" in x.value for x in app.success)
    app.run()
    assert not app.exception
    assert next(x for x in app.selectbox if x.label == "Saved revision").value == 1
    assert '"seed": 42' in app.json[0].value
