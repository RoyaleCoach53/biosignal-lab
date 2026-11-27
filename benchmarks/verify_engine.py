"""Deterministic analytical engine checks; exclusively create optional JSON report."""

from __future__ import annotations
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import numpy as np
from scipy.integrate import trapezoid
from biosignal_lab.engine import (
    Signal,
    FilterSpec,
    StreamingFilter,
    filter_signal,
    resample_signal,
    welch_psd,
    multitaper_psd,
)


def verify():
    fs = 500.0
    time = np.arange(5000) / fs
    sine = Signal((10 * np.sin(2 * np.pi * 10 * time))[None], fs, ("sine",))
    frequencies, psd = welch_psd(sine)
    mt_freq, mt_power = multitaper_psd(sine)
    high_tone = Signal((10 * np.sin(2 * np.pi * 80 * time))[None], fs, ("above_new_nyquist",))
    resampled = resample_signal(high_tone, 100.0)
    causal = FilterSpec(kind="bandpass", cutoff=(1.0, 40.0), phase="causal")
    streaming = StreamingFilter(causal, fs, 1)
    chunks = np.concatenate(
        [streaming.process(sine.data[:, :17]), streaming.process(sine.data[:, 17:])], axis=1
    )
    reference = filter_signal(sine, causal)
    targets = [
        ("welch_peak_hz", float(frequencies[np.argmax(psd[0])]), 10.0, 0.001),
        ("welch_total_power_uV2", float(trapezoid(psd[0], frequencies)), 50.0, 0.05),
        ("multitaper_total_power_uV2", float(trapezoid(mt_power[0], mt_freq)), 50.0, 0.25),
        (
            "anti_alias_output_rms_uV",
            float(np.sqrt(np.mean(resampled.data[:, 50:-50] ** 2))),
            0.0,
            0.1,
        ),
        ("chunk_max_absolute_error_uV", float(np.max(abs(chunks - reference.data))), 0.0, 1e-12),
    ]
    checks = [
        {
            "name": name,
            "measured": value,
            "target": target,
            "absolute_tolerance": tolerance,
            "passed": abs(value - target) <= tolerance,
        }
        for name, value, target, tolerance in targets
    ]
    root = Path(__file__).resolve().parents[1]
    source_hashes = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((root / "src/biosignal_lab/engine").glob("*.py"))
    }
    return {
        "schema_version": 1,
        "scope": "Synthetic analytical/reference engineering verification; no clinical or independent human-data validation",
        "python": platform.python_version(),
        "platform": platform.system(),
        "software": {name: version(name) for name in ("numpy", "scipy")},
        "source_sha256": source_hashes,
        "checks": checks,
        "passed": all(c["passed"] for c in checks),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    # Do not run and then overwrite an earlier scientific report.
    if args.output and (args.output.exists() or args.output.is_symlink()):
        parser.error("Output already exists; select a new report path")
    report = verify()
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as output:
            output.write(text)
    print(text, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
