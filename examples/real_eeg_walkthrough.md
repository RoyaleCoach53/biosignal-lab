# Reproduce the real EEG interoperability pilot

This is an educational software-consistency exercise, not a diagnostic workflow.
See [the report](../docs/real_world/REPORT.md) and [data terms](../docs/real_world/DATA_LICENSE.md).

## Prepare

Use Python 3.10+ and a virtual environment; check out the fixed Research Alpha tag:

```sh
git clone --branch v0.3.0 https://github.com/RoyaleCoach53/biosignal-lab.git
cd biosignal-lab
python -m venv .venv
# Activate .venv for your shell before installing:
python -m pip install --upgrade pip
python -m pip install -e ".[dev,all]"
python -m pytest -ra
```

## Fetch and validate

```sh
python benchmarks/real_world/validate.py --download --cache ../biosignal-lab-data --output local-results/real-world.json
python tools/physionet_pilot.py --data-dir ../biosignal-lab-data --output local-results/baseline.json
python benchmarks/performance.py --output local-results/performance.json
```

The expanded run downloads nine checksum-pinned files (about 15.4 MB) from the
official PhysioNet dataset. The six-file baseline then reuses the same cache
without network access. Omitting `--download` always requires existing valid files.
Do not place human recordings inside the repository or upload them to GitHub.

## Read the result correctly

`passed` applies only to the declared software checks. Inspect each record, the
`failures` list, exact versions, protocol hash, source hash, units, and numerical
errors. A failure is not silently removed. The baseline retains full recordings;
the expanded protocol analyzes the first 60 seconds. Their outputs answer different
questions and should not be pooled as independent participants.

The expanded JSON records hashes of its runner and core processing source files;
the baseline records runner/decoder hashes. These bind the recorded results to
exact source content, in addition to the protocol and dataset hashes.

The primary comparison matches filter padding and Welch parameters explicitly.
The separate `mne_native_padding` results show that changing edge policy can make
a material difference even after trimming. Changing a filter or window changes
the measurement; it is not automatically a defect or a physiological effect.

The Streamlit Spectrum view overlays raw and processed PSD using matched window
settings. Channel Quality shows both raw and processed summaries. Use them to
understand the selected notch and filter response; do not infer artifact absence
from low post-notch interference or a zero candidate count. Choose mains frequency
using recording metadata and spectral inspection rather than an assumed default.

No electrodes, references, task annotations or populations are interpreted as
clinical ground truth. Start with the synthetic fixtures before sharing any data.
