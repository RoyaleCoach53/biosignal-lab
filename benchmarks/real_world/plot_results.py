"""Plot derived summary statistics only; never recording samples."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["svg.hashsalt"] = "biosignal-lab-v03"


def plot(input_path, output):
    report = json.loads(Path(input_path).read_text(encoding="utf-8"))
    records = report["records"]
    labels = [r["id"] for r in records]
    x = np.arange(len(records))
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    native = [r["sensitivity"]["mne_native_padding"] for r in records]
    axes[0].bar(x - .18, [100*r["whole_record_relative_l2"] for r in native], .36, label="Whole 60 s")
    axes[0].bar(x + .18, [100*r["interior_relative_l2"] for r in native], .36, label="5 s trimmed each end")
    axes[0].set_ylabel("Waveform relative L2 difference (%)")
    axes[0].set_title("Different MNE padding policy")
    axes[0].legend(frameon=False)
    axes[1].plot(x, [r["sensitivity"]["highpass_1hz"]["median_delta_power_ratio"] for r in records], "o-", label="1 Hz high-pass: delta")
    axes[1].plot(x, [r["sensitivity"]["lowpass_40hz"]["median_gamma_power_ratio"] for r in records], "s-", label="40 Hz low-pass: gamma")
    axes[1].axhline(1, color="grey", linestyle="--", linewidth=1)
    axes[1].set_ylabel("Median channel power / default-policy power")
    axes[1].set_title("Processing-parameter sensitivity")
    axes[1].legend(frameon=False, loc="upper right")
    for axis in axes:
        axis.set_xticks(x, labels, rotation=45, ha="right")
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=.15)
        axis.set_axisbelow(True)
    fig.suptitle("Real EEG interoperability pilot: matching parameters matters", fontsize=14)
    fig.text(.02, .02, "Derived from PhysioNet EEG Motor Movement/Imagery Dataset v1.0.0 (Schalk, 2009), ODC-By-1.0.\nThree participants; nine recordings; no clinical or population inference. Dataset and license links are in the accompanying report.", fontsize=8)
    fig.tight_layout(rect=(0, .11, 1, .94))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {"Creator": "BioSignal Lab numerical pilot"}
    if output.suffix.lower() == ".svg":
        metadata["Date"] = None
    fig.savefig(output, dpi=160, metadata=metadata)
    if output.suffix.lower() == ".svg":
        text = output.read_text(encoding="utf-8")
        output.write_text("\n".join(line.rstrip() for line in text.splitlines())+"\n", encoding="utf-8", newline="\n")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plot(args.input, args.output)
