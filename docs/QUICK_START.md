# Five-minute Quick Start

For biomedical engineering students. Goal: inspect a known synthetic EEG, explain
the axes, and export a reproducible summary. No patient data, account, API key or
dataset download is needed. **Five minutes is a proposed exercise budget after
installation, not a measured learner completion time or download guarantee.**

## Install once

Install Python 3.10+ and Git first; Windows/Linux Python 3.10/3.12 are the tested
release matrix. macOS instructions are provided but not yet independently verified.
Use a terminal in a directory where you can create a project folder.

```sh
git clone --branch v0.3.0 https://github.com/RoyaleCoach53/biosignal-lab.git
cd biosignal-lab
python -m venv .venv
```

Windows PowerShell (activation is unnecessary, so no execution-policy change):

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install ".[app]"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Linux/macOS:

```sh
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install ".[app]"
.venv/bin/python -m streamlit run app.py
```

Use `python3` for the initial virtual-environment command if your system requires
it. Package downloads can take several minutes or longer. Start from the project
directory so the local-only Streamlit configuration is loaded. Open the localhost
address printed by the terminal; stop the server with Ctrl+C when finished.
The source checkout is required for `app.py`; the release wheel provides API/CLI.

## 0:00–1:00 — Know what you are looking at

Keep **Synthetic demo**, **EEG**, 250 Hz, 30 seconds, eight channels, seed 42.
The signal is generated, not recorded from a person. Read the research-only
notice. Startup notes about padding/notch behavior are expected cautions, not an
installation failure. Orange shading marks heuristic review candidates.

In **Signal Explorer**, select a channel. The horizontal axis is seconds; vertical
axis is microvolts (µV). Compare raw and filtered traces. Do not interpret a
simulated burst as a disease or the candidate count as diagnostic accuracy.

## 1:00–2:30 — Explain a spectrum

Choose **Spectrum**. The dotted raw and solid processed traces use matched Welch
settings. Frequency is in hertz; PSD is displayed in dB relative to µV²/Hz.
The default four-second segment gives a 0.25 Hz frequency grid at 250 Hz.
Grid spacing is not proof that nearby sources are physiologically separable.

The 50 Hz notch changes power around 50 Hz. It cannot demonstrate that the
original recording had no interference. Band power below the plot is an integral
in µV², not PSD in µV²/Hz or a percentage. Relative powers, when exported, use the
documented observed-band denominator; compare only matching settings.

## 2:30–3:30 — Compare quality before and after processing

Open **Channel Quality** and compare raw/processed RMS and mains fractions.
RMS describes amplitude under the selected processing. Low post-notch mains
power does not prove good acquisition. In **Artifact Review**, inspect a marked
window rather than accepting the heuristic label as ground truth.

## 3:30–5:00 — Export and explain

Open **Export**. Download the JSON summary, HTML report and processing configuration.
Confirm the JSON version is `0.3.0`, sampling rate is 250 Hz, and channel count is
eight. The report should retain the research-only disclaimer. Change the spectral
window once and notice the grid change; restore four seconds before comparisons.

You are done when you can answer: What are µV, µV²/Hz and µV²? Which samples are
raw versus processed? Why is a low residual mains fraction not a clean-data label?
What settings must accompany an exported result?

## If something goes wrong

| Symptom | Check |
| --- | --- |
| Python/Git command absent | Install the prerequisite; record this separately from a BioSignal defect |
| `No module named streamlit` | Use the same virtual-environment Python for install and launch; install `.[app]` |
| `app.py` not found | Enter the cloned project folder; the wheel alone does not include the dashboard |
| EDF support absent | Install `.[all]`; synthetic/CSV use does not require MNE |
| Port already in use | Add `--server.port 8502`; keep the server bound to localhost |
| Warning after filtering | Read the processing note and [methods](METHODS.md); do not hide it by changing arbitrary parameters |

Use [the reproducible problem template](../.github/ISSUE_TEMPLATE/bug_report.md)
for a redacted synthetic reproduction. Never attach personal recordings, full
local paths, credentials or identifying screenshots. Next: [real EEG lesson](EEG_TUTORIAL.md),
[screenshots](SCREENSHOTS.md), [beta testing](beta/PROGRAM.md), [limitations](LIMITATIONS.md).
