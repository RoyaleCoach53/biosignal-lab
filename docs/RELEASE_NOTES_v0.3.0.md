# BioSignal Lab v0.3.0 — Research Alpha

Real EEG interoperability pilot, reproducible evidence and clearer raw/processed
comparisons. Research and education only: no diagnosis, clinical approval or
independent physiological validation is claimed.

## Changes

- Hardened the incoming six-record PhysioNet baseline runner with official hashes,
  separate EDF digital-to-physical decoding, cohort controls and negative-PSD rejection.
- Added a predeclared nine-record EEG protocol: subjects 001–003, runs 01/02/04,
  64 channels, first 60 seconds at 160 Hz. Compared units, channels, filtering,
  Welch PSD, band integration and channel metrics with explicitly matched references.
- Added missing/corrupt-data controls, processing-parameter sensitivity, offline
  regression tests and official-source, checksum-pinned opt-in downloads.
- Added raw/processed spectrum overlays, raw channel summaries, and explicit
  software/padding metadata. Existing processing defaults remain unchanged.
- Added real-data/security CI, synthetic timing/allocation benchmarks, educational
  reproduction instructions, attribution and staged v1.0 acceptance criteria.

## Verification

- **107 automated tests**, zero failures/skips in the full validation environment.
- **12/12 synthetic checks**, **6/6 baseline cases**, **9/9 expanded cases**.
- A fresh-cache review reproduced the prior development reports exactly; release
  runs record version 0.3.0 and retain the same protocol, tolerances and numerical results.
- v0.2.0 comparison covered 12 API cases and 36 bit-identical numerical arrays.
  Existing signatures, positional result construction, CLI help and summary values
  were preserved. New report keys and the padding warning are additive.
- Source/wheel builds, package smoke checks, critical lint, compilation, local
  links, publication scans and dependency checks gate release publication.
- Final commit CI and artifact hashes are recorded on the release page. Consult
  [the verification record](RELEASE_VERIFICATION_v0.3.0.json) for local evidence.

The six baseline and nine expanded cases overlap; they are not 15 independent
participants or recordings. Timing measurements are synthetic and hardware-specific;
traced allocations are not process RSS or a throughput guarantee.

## Scientific limitations

MNE and BioSignal Lab share SciPy routines. Matched-policy agreement is evidence
of technical interoperability under explicit settings, not independent scientific
ground truth. Native MNE IIR padding yields **10.28–25.40%** waveform relative L2
differences, or **3.89–12.97%** after trimming five seconds at both ends. Neither
padding policy is declared physiologically correct; five-second trimming is not
a general transient-removal rule for the 0.1 Hz high-pass.

Only three convenience-selected participants were evaluated. No expert artifact
labels, detection sensitivity/specificity, task-classification accuracy, real human
EMG benchmark, device calibration, external peer review or clinical/regulatory
validation is established. Artificial bursts/flatlines are software controls.
Processing is offline, acausal and in-memory. Arbitrary EDF variants, extreme
inputs and huge files remain unsupported or incompletely characterized.

## Data rights and privacy

Contains information derived from the [PhysioNet EEG Motor Movement/Imagery
Dataset v1.0.0](https://physionet.org/content/eegmmidb/1.0.0/), Schalk, G. (2009),
DOI [10.13026/C28G6P](https://doi.org/10.13026/C28G6P), made available under the
[ODC Attribution License v1.0](https://physionet.org/content/eegmmidb/view-license/1.0.0/).
Instrumentation: Schalk et al. (2004), BCI2000, IEEE TBME 51(6):1034–1043.
PhysioNet platform: Pollard et al. (2026),
[doi:10.1038/s44360-026-00096-z](https://doi.org/10.1038/s44360-026-00096-z).

No human EDFs, waveforms, annotation streams or personal EDF headers are shipped.
Only derived summaries, hashes and protocols are included with attribution.
Dataset contents are not relicensed under MIT; code and synthetic fixtures remain MIT.
Review source/channel labels in your own exports before sharing. Security checks
are scoped reviews, not a guarantee against unknown vulnerabilities.

## Reproduce and contribute

Use the fixed `v0.3.0` tag and the [installation instructions](../README.md),
[real EEG walkthrough](../examples/real_eeg_walkthrough.md),
[full scientific report](real_world/REPORT.md), [methods](METHODS.md) and
[limitations](LIMITATIONS.md). The release wheel installs the API/CLI; the source
distribution/repository includes the dashboard, tests, examples and benchmarks.
No PyPI publication is claimed.

Start with the [beginner contribution issues and acceptance roadmap](../ROADMAP.md).
Reproduction feedback and independent methods review are especially useful.
The immutable v0.2.0 release is preserved. v0.3.0 remains Research Alpha; v1.0
requires broader evidence, independent review and explicit acceptance criteria.
