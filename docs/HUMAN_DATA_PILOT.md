# PhysioNet baseline interoperability pilot

**v0.3.0 Research Alpha evidence.** The reviewed implementation was merged in
PR #4, preserving the original incoming pilot commits and the public v0.2.0 release.
No independent external scientific or clinical validation is claimed.

## Frozen baseline protocol

Subjects 001, 002, 003; runs 01 (eyes open) and 02 (eyes closed), six files.
Use the full delivered recordings, 64 EEG channels, 160 Hz, original reference,
mean removal only, no digital notch/high/low pass. Welch: four-second Hann,
50% overlap, per-segment mean removal, density scaling. MNE and BioSignal Lab
see identical processed samples for this narrow PSD cross-check.

Acceptance remains `abs(error) <= 1e-10 + 1e-7*abs(reference)` in µV²/Hz,
with equal grids/shapes and finite nonnegative PSD values. All requested cases
must pass; no file or channel is silently excluded. Current full baseline result:
**6/6 passed**, with independent EDF unit errors below 1e-8 µV. See
[baseline-results.json](real_world/baseline-results.json).

## Review fixes

The original script's six cases passed its narrow check before hardening. Review
found gaps in official-hash verification, input-unit independence, cohort selection,
negative PSD validation, download/configuration coupling and path disclosure.
The fixed runner verifies pinned official hashes before import, independently
decodes digital EDF scaling, restricts to the declared cohort, rejects negative
PSD, labels partial selections, keeps caches outside the checkout and redacts
local paths from failure reports. Download remains explicitly opt-in.

```sh
python -m pip install -e ".[dev,all]"
python tools/physionet_pilot.py --download --subjects 1 2 3 --runs 1 2 --data-dir ../biosignal-lab-data --output local-results/baseline.json
```

Older nested MNE caches remain readable if exactly one correctly hashed file is
found. Unpinned subjects are deliberately unsupported by this frozen pilot;
extend the manifest/protocol through a reviewed change rather than silently
changing the cohort. The default cache moved outside the repository for privacy.

## Expanded protocol and limits

The separately predeclared nine-file protocol adds run 04 and uses only the first
60 seconds, default filtering, independent EDF scaling, explicitly matched MNE
filters, independent band integration, channel metrics and parameter sensitivity.
It does not alter the baseline's filter-free full-recording protocol. See
[the complete report](real_world/REPORT.md), including the non-equivalence finding
for MNE-native padding, [reproduction](../examples/real_eeg_walkthrough.md), and
[license/attribution](real_world/DATA_LICENSE.md).

MNE and SciPy share numerical routines; technical agreement is not independent
physiological truth. No artifact sensitivity/specificity, human EMG validation,
clinical outcome, hardware calibration, or external peer review is established.
