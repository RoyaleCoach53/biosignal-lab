"""Publication and report preservation controls; all data are synthetic."""
from pathlib import Path
import subprocess

import pytest

from biosignal_lab.cli import main
from tools.check_publication import scan
from tools import check_installation


@pytest.mark.parametrize("name", ["record.EDF", "record.eDf.gz", "record.BDF", "record.FIF", "record.XDF", "record.GDF", "secret.CSV"])
def test_publication_rejects_mixed_case_and_compressed_recordings(tmp_path, name):
    (tmp_path / name).write_bytes(b"synthetic")
    assert scan(tmp_path, [name]) == [f"Unapproved recording/data file: {name}"]


def test_publication_fails_closed_for_unreadable_and_symlink(tmp_path):
    assert scan(tmp_path, ["missing.txt"]) == ["Unreadable publication file: missing.txt"]
    try:
        (tmp_path / "link.txt").symlink_to(tmp_path / "missing.txt")
    except OSError:
        pytest.skip("Host does not support unprivileged symlinks")
    assert scan(tmp_path, ["link.txt"]) == ["Unreviewed symbolic link: link.txt"]


def test_audit_subprocess_removes_inherited_python_paths(monkeypatch):
    monkeypatch.setenv("PYTHONPATH", "/untrusted-checkout")
    monkeypatch.setenv("PYTHONHOME", "/untrusted-runtime")
    def fake_run(*args, **kwargs):
        assert "PYTHONPATH" not in kwargs["env"]
        assert "PYTHONHOME" not in kwargs["env"]
        assert kwargs["env"]["PYTHONNOUSERSITE"] == "1"
        return subprocess.CompletedProcess(args, 0, stdout="done")
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert check_installation.command(["python"]) == "done"


def test_audit_rejects_dangling_destination_symlink_before_creation(tmp_path):
    destination = tmp_path / "link"
    try:
        destination.symlink_to(tmp_path / "absent", target_is_directory=True)
    except OSError:
        pytest.skip("Host does not support unprivileged symlinks")
    with pytest.raises(ValueError, match="symlink"):
        check_installation.audit(destination, tmp_path / "report.json")
    assert not (tmp_path / "absent").exists()


def test_cli_demo_preserves_previous_output_unless_explicit(tmp_path):
    output = tmp_path / "demo.csv"
    output.write_text("original")
    with pytest.raises(SystemExit):
        main(["demo", "--output", str(output)])
    assert output.read_text() == "original"
    assert main(["demo", "--output", str(output), "--overwrite"]) == 0
    assert output.read_text().startswith("time_s,")


def test_cli_preserves_stale_optional_table_before_writing_other_reports(tmp_path):
    source = Path(__file__).resolve().parents[1] / "examples/data/eeg_demo.csv"
    base = tmp_path / "report"
    stale = tmp_path / "report_artifacts.csv"
    stale.write_text("previous study")
    args = ["analyze", "--input", str(source), "--sfreq", "250", "--time-column", "time_s", "--output", str(base)]
    with pytest.raises(SystemExit):
        main(args)
    assert stale.read_text() == "previous study"
    assert not base.with_suffix(".json").exists()
    assert main(args + ["--overwrite"]) == 0
    assert base.with_suffix(".json").exists()


def test_real_world_report_collision_is_rejected_before_data_access(tmp_path, monkeypatch):
    from benchmarks.real_world import validate
    report = tmp_path / "previous.json"
    report.write_text('{"passed": true}')
    monkeypatch.setattr(validate, "fetch_record", lambda *a, **k: pytest.fail("Data access reached"))
    with pytest.raises(ValueError, match="preserved"):
        validate.run(tmp_path / "cache", False, report)
    assert report.read_text() == '{"passed": true}'


def test_numeric_benchmark_rejects_previous_report_before_computation(tmp_path):
    report = tmp_path / "previous.json"
    report.write_text('{"passed": true}')
    script = Path(__file__).resolve().parents[1] / "benchmarks/verify.py"
    result = subprocess.run([__import__("sys").executable, script, "--output", report], capture_output=True, text=True)
    assert result.returncode != 0
    assert "existing scientific reports are preserved" in result.stderr
    assert report.read_text() == '{"passed": true}'


def test_cli_never_overwrites_input_even_with_overwrite(tmp_path):
    source = tmp_path / "report_quality.csv"
    main(["demo", "--output", str(source)])
    original = source.read_bytes()
    with pytest.raises(SystemExit):
        main(["analyze", "--input", str(source), "--sfreq", "250", "--time-column", "time_s", "--output", str(tmp_path / "report"), "--overwrite"])
    assert source.read_bytes() == original
