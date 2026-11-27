"""Filter and resample a deterministic synthetic EEG signal with provenance."""

from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
from biosignal_lab.engine import (
    Signal,
    FilterSpec,
    filter_signal,
    resample_signal,
    save_signal,
    welch_psd,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists() or args.output.is_symlink():
        parser.error("Output exists; choose a new path to preserve the previous experiment")
    time = np.arange(5000) / 500.0
    data = np.vstack([10 * np.sin(2 * np.pi * 10 * time), 8 * np.sin(2 * np.pi * 12 * time)])
    raw = Signal(
        data,
        500.0,
        ("synthetic_A", "synthetic_B"),
        metadata={"source": "analytic deterministic sine; no human recording"},
        reference="synthetic_zero",
    )
    processed = resample_signal(
        filter_signal(raw, FilterSpec(kind="bandpass", cutoff=(1.0, 40.0))), 100.0
    )
    frequencies, power = welch_psd(processed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save_signal(processed, args.output)
    print(
        {
            "output": str(args.output),
            "peak_frequencies_hz": frequencies[power.argmax(axis=-1)].tolist(),
            "unit": processed.unit,
            "sfreq": processed.sfreq,
            "operations": [item["operation"] for item in processed.history],
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
