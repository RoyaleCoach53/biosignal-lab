"""One checksum-pinned public EEG recording: matched MNE references and derived plots."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from benchmarks.real_world.validate import (BANDS, decode_uniform_edf, fetch_record,
        integrate_linear, reference_filter, reference_psd, validate_record, validate_manifest)
except ImportError as exc:
    raise SystemExit('Install the tutorial dependencies in this environment: python -m pip install ".[tutorial]"') from exc

from biosignal_lab import __version__
from biosignal_lab.io import read_edf
from biosignal_lab.models import AnalysisConfig
from biosignal_lab.pipeline import analyze
from tools.first_run_check import source_revision, source_state


def plot_comparison(result, frequencies, reference, reference_bands, channel, record, output):
    label = result.recording.channels[channel]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for f, p, name, style in [
        (result.raw_frequencies_hz, result.raw_psd_uv2_per_hz[channel], "Before filters", "--"),
        (result.frequencies_hz, result.psd_uv2_per_hz[channel], "BioSignal processed", "-"),
        (frequencies, reference[channel], "MNE matched settings", ":"),
    ]:
        axes[0].semilogy(f, np.maximum(p, 1e-12), style, label=name)
    axes[0].set(xlim=(0, 80), xlabel="Frequency (Hz)", ylabel="PSD (µV²/Hz)", title=f"{record['id']} · {label}")
    axes[0].legend(fontsize=8)
    x = np.arange(len(BANDS))
    ours = [result.band_powers[channel][name + "_uv2"] for name in BANDS]
    theirs = [reference_bands[name][channel] for name in BANDS]
    axes[1].bar(x - .18, ours, .36, label="BioSignal")
    axes[1].bar(x + .18, theirs, .36, label="MNE + separate integral")
    axes[1].set(xticks=x, xticklabels=list(BANDS), ylabel="Absolute band power (µV²)", title="Matched processing; original reference")
    axes[1].legend(fontsize=8)
    for axis in axes:
        axis.grid(axis="y", alpha=.2)
        axis.set_axisbelow(True)
    fig.suptitle("Public EEG software interoperability · Research Alpha", fontsize=13)
    fig.text(.02, .02, "Derived from PhysioNet EEGMMIDB v1.0.0, Schalk (2009), DOI 10.13026/C28G6P, ODC-By-1.0.\nOne recording; shared SciPy routines; no clinical or population inference. No waveforms shown.", fontsize=8)
    fig.tight_layout(rect=(0, .12, 1, .93))
    fig.savefig(output, dpi=150)
    plt.close(fig)


def run(cache: Path, output: Path, record_id="S001R01", channel=0, download=False):
    if cache.resolve().is_relative_to(ROOT):
        raise ValueError("Keep the recording cache outside the checkout")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Choose a new or empty output directory to avoid stale reports")
    folder = ROOT / "benchmarks/real_world"
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    protocol = json.loads((folder / "protocol.json").read_text(encoding="utf-8"))
    validate_manifest(manifest, protocol)
    records = [r for r in manifest["records"] if r["id"] == record_id]
    if len(records) != 1:
        raise ValueError("Choose a recording ID from the pinned manifest")
    if not isinstance(channel, int) or not 0 <= channel < 64:
        raise ValueError("Channel index must be an integer from 0 to 63")
    record = records[0]
    path = fetch_record(record, cache, download)
    validation = validate_record(record, path, protocol)
    if not validation["passed"]:
        raise ValueError("Reference gates failed; no successful tutorial output was written")
    recording = read_edf(path, max_duration_s=protocol["analysis_seconds"])
    config = AnalysisConfig(**protocol["primary_config"])
    result = analyze(recording, config)
    independent, fs, _ = decode_uniform_edf(path, protocol["analysis_seconds"])
    filtered_reference = reference_filter(independent, fs, config)
    frequencies, power = reference_psd(filtered_reference, fs, config.window_s)
    bands = {name: integrate_linear(frequencies, power, *edges) for name, edges in BANDS.items()}
    # Only derived summaries/PSD-band plots; never EDF headers, samples or annotation streams.
    report = {"schema_version": 1, "tutorial_version": 1, "software_version": __version__,
        "source_revision": source_revision(), "source_state": source_state(), "recording_id": record_id, "sha256": record["sha256"],
        "dataset_url": manifest["dataset_url"], "license_url": manifest["license_url"], "attribution": manifest["attribution"],
        "python": platform.python_version(), "packages": {n: importlib.metadata.version(n) for n in ["numpy", "scipy", "mne", "matplotlib"]},
        "protocol_sha256": hashlib.sha256((folder / "protocol.json").read_bytes()).hexdigest(),
        "manifest_sha256": hashlib.sha256((folder / "manifest.json").read_bytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "software_source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
            ["examples/eeg_tutorial.py", "benchmarks/real_world/validate.py", "src/biosignal_lab/io.py",
             "src/biosignal_lab/analysis.py", "src/biosignal_lab/preprocessing.py", "src/biosignal_lab/pipeline.py",
             "src/biosignal_lab/models.py", "src/biosignal_lab/_version.py"]},
        "sampling_hz": fs, "channels": len(recording.channels), "analysis_seconds": recording.duration_s,
        "welch_grid_hz": float(frequencies[1] - frequencies[0]), "config": config.__dict__,
        "displayed_channel_index": channel, "displayed_channel_label": recording.channels[channel],
        "selected_band_powers_uv2": {name: {"biosignal": result.band_powers[channel][name + "_uv2"], "reference": float(bands[name][channel])} for name in BANDS},
        "validation": validation, "passed": True,
        "scope": "One-record educational interoperability exercise using the unchanged v0.3 protocol; not 9/9 cohort evidence, independent physiology or clinical validation. Shared SciPy routines; native-padding differences remain in validation.sensitivity."}
    output.mkdir(parents=True, exist_ok=True)
    plot_comparison(result, frequencies, power, bands, channel, record, output / "spectrum-and-bands.png")
    (output / "tutorial-summary.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8", newline="\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("local-results/eeg-tutorial"))
    parser.add_argument("--record", default="S001R01")
    parser.add_argument("--channel", type=int, default=0)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = run(args.cache, args.output, args.record, args.channel, args.download)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"{type(exc).__name__}: tutorial input or reference checks failed. Verify the pinned ID, outside-checkout cache, checksum, --download and a new/empty --output directory.\n")
    print(f"{report['recording_id']}: matched-reference gates passed; derived plot and tutorial-summary.json written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
