"""Offline failure/privacy controls for the adoption workflows; no human fixtures."""
import json

import pytest

from tools.first_run_check import check
from tools.check_installation import audit
from biosignal_lab.ui import display_options


def test_first_run_report_is_offline_and_does_not_include_local_paths():
    report = check()
    assert report["passed"] and report["synthetic_sample_hashes_verified"]
    assert "source_revision" in report
    serialized = json.dumps(report)
    assert "C:\\" not in serialized and "/Users/" not in serialized
    assert "data_uv" not in serialized


def test_current_dashboard_api_receives_stretch_and_accessible_description():
    def current_chart(data, *, width="stretch", alt=None):
        return width, alt
    assert current_chart([], **display_options(current_chart, "PSD in microvolts squared per Hz")) == ("stretch", "PSD in microvolts squared per Hz")


def test_older_dashboard_api_receives_no_unsupported_new_keywords():
    def older_chart(data, use_container_width=False):
        return use_container_width
    assert older_chart([], **display_options(older_chart, "PSD")) is True


def test_clean_audit_refuses_existing_environment_without_modifying_it(tmp_path):
    marker = tmp_path / "leave-me.txt"
    marker.write_text("original")
    with pytest.raises(ValueError, match="nonexistent"):
        audit(tmp_path, tmp_path / "report.json")
    assert marker.read_text() == "original"


def test_tutorial_rejects_inside_repo_cache_before_network(tmp_path, monkeypatch):
    pytest.importorskip("mne")
    from examples import eeg_tutorial
    monkeypatch.setattr(eeg_tutorial, "fetch_record", lambda *a, **k: pytest.fail("Network reached"))
    with pytest.raises(ValueError, match="outside"):
        eeg_tutorial.run(eeg_tutorial.ROOT / "data", tmp_path)


@pytest.mark.parametrize("record,channel", [("S999R99", 0), ("S001R01", -1), ("S001R01", 64)])
def test_tutorial_rejects_unpinned_or_invalid_selection_without_download(tmp_path, monkeypatch, record, channel):
    pytest.importorskip("mne")
    from examples import eeg_tutorial
    monkeypatch.setattr(eeg_tutorial, "fetch_record", lambda *a, **k: pytest.fail("Network reached"))
    with pytest.raises(ValueError):
        eeg_tutorial.run(tmp_path / "cache", tmp_path / "output", record_id=record, channel=channel)


def test_tutorial_reference_failure_cannot_export_a_pass(tmp_path, monkeypatch):
    pytest.importorskip("mne")
    from examples import eeg_tutorial
    monkeypatch.setattr(eeg_tutorial, "fetch_record", lambda *a, **k: tmp_path / "unused.edf")
    monkeypatch.setattr(eeg_tutorial, "validate_record", lambda *a, **k: {"passed": False})
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="Reference gates failed"):
        eeg_tutorial.run(tmp_path / "cache", output)
    assert not output.exists()
