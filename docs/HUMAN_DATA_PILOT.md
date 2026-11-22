# PhysioNet EEGMMIDB human-data interoperability pilot

**Status: protocol and executable runner only. Human-data results have NOT yet been
collected, independently reviewed, or accepted.** This is not a v1.0 clinical
validation protocol. The work is intentionally isolated from the v0.2.0 release.

## Fixed data source and attribution

- PhysioNet **EEG Motor Movement/Imagery Database**, release **1.0.0**,
  DOI **[10.13026/C28G6P](https://doi.org/10.13026/C28G6P)**.
- Original contributors: Gerwin Schalk and colleagues, BCI R&D Program,
  Wadsworth Center, New York State Department of Health, and the BCI2000 team.
- Source: [PhysioNet EEGMMIDB](https://physionet.org/content/eegmmidb/1.0.0/).
- Dataset terms: **Open Data Commons Attribution License v1.0**. These data do
  not become MIT-licensed merely because the analysis code is MIT-licensed.
  Check and preserve dataset attribution in downstream publications.
- EDF+ recordings: **160 samples/second**; expected **64 EEG channels**.
  Annotation/event labels are **not** treated as validated clinical labels.

## Frozen selection (pilot; not representative of the entire population)

Subjects **001, 002, 003**, each with run **01 (eyes open)** and run
**02 (eyes closed)**, six files total. These are baseline recordings, not
motor-imagery classification epochs. No participants, channels, or trials may
be silently dropped. Missing or invalid files are recorded as failures;
any later exclusion must be logged with a reason before reanalysis.

## Processing and quantitative acceptance

1. Read original EDF with MNE via BioSignal Lab `read_edf` and verify
   EEG-only channel typing, 160 Hz sampling, 64 channels, finite amplitudes,
   and sample count. Conversion from MNE volts to BioSignal Lab microvolts
   is explicit.
2. Retain the reference **as recorded**. The acquisition montage/reference
   cannot be inferred from channel names alone; no automatic rereferencing
   or montage interpretation is performed. BioSignal Lab removes channel means.
   Disable notch, high-pass, and low-pass for this interoperability pilot.
3. Use **4.0 s Hann Welch segments**, 50% overlap, constant detrending,
   density scaling. Compare BioSignal Lab output in **µV²/Hz** to
   `mne.time_frequency.psd_array_welch` on the **identical processed samples**,
   with reference PSD converted from V²/Hz by multiplying by 10^12.
4. **Pass:** every requested file is present; metadata invariants hold;
   PSD frequency grids/shapes match; all PSD values are finite; for every
   compared frequency/channel bin, `abs(error) <= 1e-10 + 1e-7*abs(reference)`
   in µV²/Hz. A nonzero failing-bin count fails the case and total run.
5. Report dataset URL/DOI, original EDF **SHA-256**, subjects and run IDs,
   sampling rate, channel labels, processing parameters, library versions,
   error magnitudes, warnings, and pass/fail results. No person-level
   diagnostic inference, significance testing, classifier metric, or effect
   direction is inferred from these six files.

**Important independence limitation:** both methods operate on the same
processed array; the MNE implementation and BioSignal Lab/SciPy may share
numerical routines. Agreement is therefore an **interoperability and units
check**, NOT independent ground-truth verification, external peer review,
proof of physiological validity, or a sensitivity/specificity estimate.

## Reproduce (opt-in external download)

From a clean checkout on Python 3.10+:

```sh
python -m pip install -e ".[dev,all]"
python -m pytest -ra
python tools/physionet_pilot.py --download --subjects 1 2 3 --runs 1 2 --output local-results/physionet-pilot.json
```

The runner **never downloads without `--download`**. Cached EDFs may instead
be placed under `local-results/physionet-cache/` (nested directories are
searched for files like `S001R01.edf`). A failure exits nonzero and emits
a machine-readable JSON report. Raw recordings and reports stay in
`local-results/` and are excluded by `.gitignore`; review manually before
sharing any case metadata. Do not publish EDF files or participant-derived
samples as part of this code repository.

## Requirements for further research claims

- Review the acquisition reference, electrode metadata, annotations, and
  EDF channel types against primary dataset documentation.
- Add fully specified, independently implemented spectral references and
  blind review of any disagreements; account for band edges and filters.
- For artifact-detection accuracy, obtain independent human annotations and
  define event matching and uncertainty intervals *before* evaluating.
- For cross-subject claims, freeze a subject-disjoint split, report
  per-subject metrics and uncertainty, and prevent preprocessing leakage.
- Obtain independent biomedical-signal-processing review before any
  scientific validity language is promoted into the README or release notes.

Until then, the project remains research/education software, with no
diagnostic, clinical, regulatory, or real-time safety-critical capability.
