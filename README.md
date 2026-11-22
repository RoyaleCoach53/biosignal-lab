# BioSignal Lab

**A local EEG and EMG signal-analysis toolkit for biomedical engineering education and research.**

[![Tests and numerical verification](https://github.com/RoyaleCoach53/biosignal-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/RoyaleCoach53/biosignal-lab/actions/workflows/ci.yml)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Inspect recordings, compare raw and filtered signals, examine spectral content,
and export reproducible summaries without an API key or cloud account.
**Development branch: proposed v0.3.0 (0.3.0.dev0), review pending.** The current
public release remains **v0.2.0 Research Alpha**. This work adds a real-EEG
technical interoperability pilot; it does not establish clinical validation.

## What you can do

- Import numeric CSV channels with explicit amplitude units and sampling rate;
  optionally import EDF through MNE with separate EEG/EMG channel selection.
- Explore raw and processed waveforms, Welch PSD, spectrograms, and EEG band powers.
- Compute RMS, peak-to-peak, variability, Hjorth descriptors, residual mains ratios,
  and EMG mean absolute value, waveform length, and median frequency.
- Review heuristic amplitude-outlier and flatline windows on the unfiltered signal.
- Compare channel coherence when sufficient data and nonconstant channels are available.
- Export JSON, self-contained HTML, channel statistics CSV, and processing settings.
- Start with deterministic synthetic demos and two redistributable sample CSV files.

**Research and education only.** No diagnosis, seizure detection, clinical signal
approval, or safety-critical control is provided. Quality flags are review aids.

## Install

Use Python 3.10 or newer. Clone this repository and create a virtual environment:

```sh
git clone --branch research/physionet-validation-v03 https://github.com/RoyaleCoach53/biosignal-lab.git
cd biosignal-lab
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` on Windows PowerShell, or
`source .venv/bin/activate` on macOS/Linux. Then install:

```sh
python -m pip install --upgrade pip
python -m pip install -e ".[app]"
streamlit run app.py
```

Open the local address printed by Streamlit. The project configuration binds to
`127.0.0.1` and disables usage statistics. Choose **Synthetic demo**, then explore
the signal, spectrum, time-frequency, quality, artifact, and export tabs.

For EDF and the dashboard together, install `python -m pip install -e ".[all]"`.
For only the Python library and CLI, use `python -m pip install -e .`.
There is no claim that this project has been published on PyPI. The release wheel
installs the library and CLI; use the repository or source distribution for `app.py`.

## Try the included samples

```sh
biosignal-lab analyze --input examples/data/eeg_demo.csv --sfreq 250 --unit uv --time-column time_s --output local-results/eeg
biosignal-lab analyze --input examples/data/emg_demo.csv --sfreq 2000 --modality emg --unit uv --time-column time_s --output local-results/emg
```

Outputs include `.json`, `.html`, and `_quality.csv`; EEG band and artifact CSVs
are created when applicable. [Sample documentation](examples/README.md) describes
columns, units, provenance, checksums, and regeneration.

Generate another deterministic demo:

```sh
biosignal-lab demo --output local-results/demo.csv --duration 30 --sfreq 250 --channels 8
biosignal-lab analyze --input local-results/demo.csv --sfreq 250 --time-column time_s --output local-results/demo
```

## Python API

```python
from biosignal_lab import analyze
from biosignal_lab.simulate import synthetic_recording

recording = synthetic_recording(duration_s=30, sfreq=250, n_channels=2, seed=42)
result = analyze(recording)
print(result.band_powers)
print(result.warnings)
```

CSV files have one signal channel per column. Supply `--sfreq` in Hz and
`--unit uv|mv|v`; specify `--time-column` for timestamp columns in seconds.
Timestamp spacing is checked, not silently inferred. Data are represented in
microvolts internally. See `biosignal-lab analyze --help` for filter overrides.

## Verified numerical behavior

The original archive's **73 tests were reproduced unchanged before release fixes**.
The current development suite has **107 passing tests locally with no skips**;
the v0.2.0 release had 85. The incoming research branch and its original tests are preserved.
The test suite includes a generated mixed EEG/EMG EDF file and a matched-setting
MNE PSD comparison. A separate benchmark command passes **12 numerical checks**.

| Synthetic input | Theoretical target | Reproduced output |
| --- | --- | --- |
| 10 µV peak, 2 Hz tone | 50 µV² delta power | 50.00344 µV² |
| 10 µV peak, 10 Hz tone | 50 µV² alpha power | 49.99376 µV² |
| 10 µV peak, 35 Hz tone | 50 µV² gamma power | 49.75934 µV² |
| 10 µV peak, 42 Hz tone | 50 µV² gamma power | 49.02989 µV² |
| 100 µV peak, 200 Hz; 500 Hz sampling | 70.71068 µV RMS | 70.71580 µV |
| 100 µV peak, 200 Hz; 2000 Hz sampling | 70.71068 µV RMS | 70.70170 µV |

Values refer to the documented filtering, duration, and estimator settings, not
unfiltered physiological ground truth. The 500 Hz EMG case checks preservation of
a representable tone; it does not validate full-band surface EMG at that rate.
The MNE PSD comparison has maximum absolute error about **7.11e-14 µV²/Hz** in the
recorded environment. MNE and SciPy can share underlying numerical routines.

```sh
python -m pip install -e ".[dev,all]"
python -m pytest -ra
python benchmarks/verify.py --output local-results/verification.json
```

CI runs the suite, benchmarks, critical Python lint, compilation, documentation
links, and package builds on Windows and Linux with Python 3.10 and 3.12.
It uploads per-environment results. See [benchmark reproduction](benchmarks/README.md),
[current audit](docs/SCIENTIFIC_AUDIT.md), and [machine-readable measurements](docs/VERIFICATION_RESULTS.json).

## Real EEG interoperability pilot — development evidence

The [full report](docs/real_world/REPORT.md) covers nine checksum-pinned PhysioNet
recordings from three subjects: eyes-open/closed baselines and motor-imagery runs,
64 channels, first 60 seconds at 160 Hz. **9/9 records passed** the predeclared
matched-reference gates; the preserved full-recording baseline also passed **6/6**.
EDF scaling is checked with a separate digital decoder, filters/PSD with explicitly
configured MNE, and band integration with a separate implementation.

**Important non-equivalence:** MNE's native padding policy differs by roughly
10–25% in waveform relative L2 on these recordings; differences remain after
five-second edge trimming. Shared SciPy routines and matched settings limit the
independence of the numerical comparison. This is not physiological or clinical validation.

The dashboard now overlays raw/processed spectra, exposes raw channel metrics,
and records explicit padding/software versions in reports. Human recordings are
not shipped. Read [data attribution](docs/real_world/DATA_LICENSE.md) and the
[reproducible walkthrough](examples/real_eeg_walkthrough.md).

## Scientific boundaries

- EEG defaults use a 0.1 Hz high-pass, no low-pass, and a 50 Hz notch when supported.
  EMG defaults and bandwidth warnings are documented in [Methods](docs/METHODS.md).
- Unsupported EEG frequency bands are `null`, not measured zero power.
- Missing-data interpolation is limited to short interior gaps; long and boundary gaps are rejected.
- Preprocessing removes channel means. RMS describes the processed signal, not an original DC offset.
- Filtering is offline and acausal. Hardware anti-aliasing and reference choices remain the user's responsibility.
- The small PhysioNet EEG pilot verifies technical interoperability under explicit
  processing settings. No independent physiological/clinical validation, artifact
  sensitivity/specificity, real EMG benchmark, hardware validation or regulatory approval is established.

Read [scientific limitations](docs/LIMITATIONS.md) before interpreting any output.

## Privacy and security

Processing runs wherever Python is running. Local execution does not require
cloud uploads; a remotely hosted dashboard processes files on its host. Reports
contain summaries and source/channel names, so review them before sharing.
Do not upload identifiable recordings to public instances or GitHub issues.
See [SECURITY.md](SECURITY.md) for private vulnerability reporting.

## Project and community

[Contributing](CONTRIBUTING.md) · [Code of conduct](CODE_OF_CONDUCT.md) ·
[Roadmap](ROADMAP.md) · [Changelog](CHANGELOG.md) · [Architecture](docs/ARCHITECTURE.md) ·
[Release status](docs/RELEASE_STATUS.md) · [Attribution](NOTICE.md)

Useful next contributions include an independent methods review, a small licensed
human-data benchmark, accessibility feedback, and reproducible issue reports.
The project is MIT licensed; dependencies retain their own licenses.
