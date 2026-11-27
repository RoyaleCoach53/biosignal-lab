"""Render a deterministic simulated event average and scalp map (no human data)."""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from biosignal_lab.engine import (
    Signal,
    epoch,
    plot_evoked,
    plot_topomap,
    scalp_positions,
    save_signal,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="New directory; existing experiments are never overwritten",
    )
    args = parser.parse_args(argv)
    if args.output_dir.exists() or args.output_dir.is_symlink():
        parser.error("Output directory exists; choose a new experiment directory")
    # Gaussian event-locked pulses are a mathematical educational fixture, not
    # claims about a physiological P300 or another particular evoked component.
    fs, n = 100.0, 3200
    rng = np.random.default_rng(42)
    data = rng.normal(0.0, 0.7, size=(6, n))
    event_samples = np.arange(200, 3000, 300)
    weights = np.array([0.4, 0.5, 0.8, 1.0, 0.3, 0.2])
    offsets = np.arange(-20, 81)
    for sample in event_samples:
        pulse = 10 * np.exp(-0.5 * ((offsets / fs - 0.3) / 0.06) ** 2)
        data[:, sample + offsets] += weights[:, None] * pulse
    raw = Signal(
        data,
        fs,
        ("Fp1", "Fp2", "C3", "C4", "O1", "O2"),
        reference="synthetic_zero",
        metadata={
            "source": "deterministic Gaussian mathematical event fixture; no human data",
            "seed": 42,
        },
    )
    trials = epoch(raw, event_samples, -0.2, 0.8, baseline=(-0.2, 0))
    average = trials.average()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    import matplotlib.pyplot as plt

    evoked = plot_evoked(trials)
    evoked.savefig(args.output_dir / "event-average.png", dpi=140)
    peak_sample = int(round((0.3 - trials.times[0]) * fs))
    scalp = plot_topomap(average, average.data[:, peak_sample], value_unit=average.unit)
    scalp.savefig(args.output_dir / "scalp-at-0p3s.png", dpi=140)
    save_signal(average, args.output_dir / "event-average.npz")
    report = {
        "scope": "Synthetic engineering demonstration; no physiological component inference",
        "seed": 42,
        "event_samples": event_samples.tolist(),
        "sfreq_hz": fs,
        "baseline_s": [-0.2, 0.0],
        "topomap_time_s": float(trials.times[peak_sample]),
        "positions": scalp_positions(raw),
        "operations": [item["operation"] for item in average.history],
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    plt.close(evoked)
    plt.close(scalp)
    print(
        f"Rendered {len(event_samples)} synthetic trials, saved real plots and provenance to {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
