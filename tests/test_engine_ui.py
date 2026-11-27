from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest


def test_engine_ui_real_processing_units_and_rejected_filter():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "engine_app.py"),
                            default_timeout=30).run()
    assert not app.exception
    assert not app.error
    assert len(app.get("plotly_chart")) == 2
    next(x for x in app.selectbox if x.label == "Measurement modality").set_value("eda")
    next(x for x in app.selectbox if x.label == "Physical unit").set_value("uS").run()
    assert not app.exception and not app.error
    assert any("uS²/Hz" in x.value for x in app.caption)
    next(x for x in app.selectbox if x.label == "Filter family").set_value("fir").run()
    assert not app.exception and not app.error
    next(x for x in app.number_input if x.label == "FIR taps (odd)").set_value(32).run()
    assert not app.exception
    assert any("odd tap count" in x.value for x in app.error)
