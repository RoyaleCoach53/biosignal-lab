# Scientific limitations

## Current evidence

The historical source archive is not yet recovered into this checkout. No
implementation-specific calculation, test count, dependency audit, or benchmark
is independently verified by this repository at this stage.

## Numerical validation and clinical validation

Tests on known signals can reveal unit, scaling, filter, spectral-integration,
and parsing defects. Agreement with a second library under matched settings
checks computational consistency, but both implementations may share assumptions
or underlying routines. Neither establishes diagnostic performance or clinical safety.

Human recordings introduce acquisition differences, artifacts, reference choices,
electrode placement, population variation, and annotation uncertainty. Evaluation
requires a defined task, suitable data, predeclared metrics, and an appropriate
study design. Performance claims must state their dataset and evaluation limits.

## Interpretation requirements

- Document signal units, sensor type, channel type, and acquisition context.
- State EEG frequency-band boundaries; conventions vary and boundaries are not diagnoses.
- A filter changes the measured signal. Report its response and transition bands.
- Forward-backward filtering is an offline operation and does not establish real-time behavior.
- Sampling rate alone does not prove that a device acquired a usable frequency band.
- Short recordings and short spectral windows limit frequency resolution.
- Do not silently treat missing, unsupported, or rejected measurements as zero.
- EMG RMS depends on the processing window, bandwidth, units, and artifacts.
- Quality flags are review aids until their behavior is evaluated against suitable labels.
- Any missing-data interpolation requires explicit limits and disclosure.

BioSignal Lab is intended for education and research. It must not be used to make
diagnosis, treatment, or emergency-care decisions. No regulatory approval,
medical-device status, or clinical validation is claimed.
