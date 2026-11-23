"""Opt-in clean-install audit in a NEW outside-checkout virtual environment."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def command(arguments, cwd=ROOT):
    completed = subprocess.run([str(x) for x in arguments], cwd=cwd, capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
                                        STREAMLIT_BROWSER_GATHER_USAGE_STATS="false"))
    if completed.returncode:
        raise RuntimeError(f"Audit command failed with exit {completed.returncode}; no private command output was exported")
    return completed.stdout


def audit(destination: Path, output: Path):
    destination = destination.resolve()
    if destination.exists() or destination.is_relative_to(ROOT):
        raise ValueError("Use a new, nonexistent virtual-environment directory outside the checkout")
    venv.EnvBuilder(with_pip=True, system_site_packages=False).create(destination)
    python = destination / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")
    before = json.loads(command([python, "-m", "pip", "list", "--format=json"]))
    if {x["name"].lower() for x in before} - {"pip", "setuptools", "wheel"}:
        raise RuntimeError("Unexpected initial packages; clean-environment gate failed")
    isolation = json.loads(command([python, "-c", "import json,sys,site; print(json.dumps({'venv':sys.prefix!=sys.base_prefix,'user_site':site.ENABLE_USER_SITE}))"]))
    if not isolation["venv"] or isolation["user_site"]:
        raise RuntimeError("Environment is not isolated")
    command([python, "-m", "pip", "install", "--no-cache-dir", "--upgrade", "pip"])
    command([python, "-m", "pip", "install", "--no-cache-dir", ".[app]"])
    command([python, "-m", "pip", "check"])
    # These are synthetic outputs only, kept beside the disposable environment.
    scratch = destination.parent / (destination.name + "-results")
    scratch.mkdir(exist_ok=True)
    first = json.loads(command([python, ROOT / "tools/first_run_check.py", "--require-app"]))
    if not first["passed"]:
        raise RuntimeError("Offline first-use gate failed")
    for modality, fs in [("eeg", 250), ("emg", 2000)]:
        base = scratch / modality
        command([python, "-m", "biosignal_lab.cli", "analyze", "--input", ROOT / f"examples/data/{modality}_demo.csv",
                 "--sfreq", fs, "--modality", modality, "--time-column", "time_s", "--output", base])
        summary = json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))
        if summary["version"] != first["version"] or not summary["channels"] or not base.with_suffix(".html").is_file():
            raise RuntimeError("Packaged CLI/report gate failed")
    app_script = (
        "from streamlit.testing.v1 import AppTest; "
        "import sys; a=AppTest.from_file(sys.argv[1],default_timeout=60).run(); "
        "assert not a.exception; assert len(a.metric)>=4; print('dashboard-smoke-passed')"
    )
    command([python, "-c", app_script, ROOT / "app.py"])
    packages = json.loads(command([python, "-m", "pip", "list", "--format=json"]))
    report = {"schema_version": 1, "scope": "Clean virtual environment and source-wheel install on an existing OS/Python/Git host; not a fresh operating-system or independent learner study.",
              "source_revision": first["source_revision"], "python": first["python"], "os": first["os"],
              "initial_packages": before, "isolation": isolation, "installation": ".[app], noneditable, pip --no-cache-dir",
              "dependency_consistency": True, "packaged_eeg_emg_cli_and_reports": True,
              "dashboard_apptest_no_exceptions": True, "first_run": first, "installed_packages": packages,
              "passed": True, "privacy": "No human data, usernames, local paths, pip credentials or raw install logs included."}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8", newline="\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venv", type=Path, required=True, help="New outside-checkout directory; never clears an existing environment")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        audit(args.venv, args.output)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"{type(exc).__name__}: clean-install audit failed; no success report generated.\n")
    print("Clean install, packaged EEG/EMG CLI, reports and dashboard smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
