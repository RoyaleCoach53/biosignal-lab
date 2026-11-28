"""Failure evidence and source-freeze guards without rebuilding distributions."""
import json
from pathlib import Path
import subprocess

import pytest

from tools.verification import final_verify as verification


def _repository(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    (root / "record.txt").write_text("frozen")
    subprocess.run(["git", "-C", str(root), "add", "record.txt"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Verification test",
                    "-c", "user.email=verification@example.invalid", "commit", "--quiet", "-m", "fixture"], check=True)
    return root, subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def test_dirty_source_refuses_build_before_output_creation(tmp_path, monkeypatch):
    root, commit = _repository(tmp_path)
    (root / "record.txt").write_text("changed after freeze")
    monkeypatch.setattr(verification.Commands, "run", lambda *a, **k: pytest.fail("Build reached dirty source"))
    output = tmp_path / "results"
    with pytest.raises(RuntimeError, match="frozen, clean"):
        verification.main(["--source", str(root), "--expected-commit", commit,
                           "--mode", "packaging", "--output", str(output)])
    assert not output.exists()


def test_build_failure_preserves_exit_code_and_never_claims_success(tmp_path, monkeypatch):
    root, commit = _repository(tmp_path)
    monkeypatch.setattr(verification, "assert_frozen", lambda *a: None)
    def fail(arguments, **kwargs):
        assert arguments[0] == "selected-python"
        assert arguments[1:3] == ["-m", "build"]
        assert "PYTHONPATH" not in kwargs["env"]
        assert "PIP_TARGET" not in kwargs["env"]
        kwargs["stdout"].write("deliberate build failure")
        return subprocess.CompletedProcess(arguments, 17)
    monkeypatch.setattr(verification.subprocess, "run", fail)
    monkeypatch.setenv("PYTHONPATH", "/untrusted/source")
    monkeypatch.setenv("PIP_TARGET", "/untrusted/target")
    output = tmp_path / "results"
    status = verification.main(["--source", str(root), "--expected-commit", commit,
                                "--python", "selected-python", "--mode", "packaging", "--output", str(output)])
    assert status == 1
    report = json.loads((output / "report.json").read_text())
    assert report["passed"] is False
    assert report["commands"][0]["exit_code"] == 17
    assert report["commands"][0]["name"] == "build"
    assert (output / "build.log").read_text() == "deliberate build failure"


def test_smoke_requires_one_complete_result_record():
    with pytest.raises(ValueError, match="one complete"):
        verification.smoke_result("VERIFICATION_JSON={}\nVERIFICATION_JSON={}")
    with pytest.raises(ValueError, match="one complete"):
        verification.smoke_result("Process exited without performing functional checks")
    assert verification.smoke_result('diagnostic\nVERIFICATION_JSON={"version":"test"}') == {"version": "test"}
