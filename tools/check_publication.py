"""Reject known raw-recording formats, unapproved CSVs, and credential patterns."""
from pathlib import Path
import re
import subprocess


def main():
    root = Path(__file__).resolve().parents[1]
    files = [p for p in subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0") if p]
    raw = {".edf", ".bdf", ".fif", ".vhdr", ".eeg", ".set", ".cnt"}
    csv_allowed = {"examples/data/eeg_demo.csv", "examples/data/emg_demo.csv"}
    patterns = [r"gh[pousr]_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{30,}",
                r"sk-proj-[A-Za-z0-9_-]{20,}", r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"]
    failures = []
    for name in files:
        path = root / name
        if set(path.suffixes) & raw or (path.suffix.lower() == ".csv" and name not in csv_allowed):
            failures.append(f"Unapproved recording/data file: {name}")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(re.search(p, text) for p in patterns):
            failures.append(f"Credential pattern in: {name}")
    print(f"Publication check: {len(files)} tracked files, {len(failures)} findings.")
    for failure in failures:
        print(failure)
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
