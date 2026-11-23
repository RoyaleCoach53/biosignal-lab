# Scientific and operational limitations

## What was verified

The original 73 automated tests were reproduced before changes. The v0.3.0
107-test suite and 12 benchmark checks cover specified synthetic inputs, parsers,
mathematical targets, matched-setting reference calculations, and dashboard flows.
See [the audit](SCIENTIFIC_AUDIT.md) and [methods](METHODS.md).

## What remains unvalidated

- Only a small public PhysioNet EEG technical-interoperability pilot is evaluated; no real EMG study or independent physiological validation.
- No diagnostic accuracy, seizure detection, patient safety, or regulatory evidence.
- No artifact sensitivity/specificity, expert labels, or population generalization.
- No acquisition hardware calibration, analog anti-alias verification, or montage assessment.
- No guarantee for arbitrary EDF variants, mislabeled channels, huge files, or extreme numeric inputs.

## Interpretation

Filters, references, electrode placement, window length, and units change metrics.
Preprocessing removes the mean; reported RMS is computed after processing.
Frequency-band conventions vary. Band-edge leakage, especially near 0.5 Hz, can
substantially underestimate nominal sinusoid power. Missing/unsupported bands are
unavailable values, not zero. Interpolation fabricates intermediate samples and
is bounded and disclosed, but can still alter measurements.

Coherence needs at least two Welch segments and nonconstant channels. That minimum
is only a guard against a degenerate estimator; it does not establish reliability,
statistical significance, or neural connectivity. Shared references and artifacts
can inflate coherence. MNE/SciPy comparisons may share numerical routines.

EMG descriptors depend on bandwidth and acquisition. A representable 200 Hz tone
at 500 Hz sampling is not evidence that broadband surface EMG is fully captured.
Median frequency alone cannot determine fatigue. Heuristic artifact flags need
human review and have not been evaluated against independent annotations.

## Operation and privacy

The pipeline is offline, acausal, and in-memory. The dashboard binds locally by
default and caps uploads at 50 MB; the core CSV API is not a streaming service.
NumPy arrays in recording objects remain mutable. Reports contain source and
channel labels and should be reviewed before sharing. Uploaded data are processed
on the server running the application; a hosted copy does not have local privacy.

Do not use BioSignal Lab to make diagnosis, treatment, emergency-care, or
safety-critical control decisions.

## Real-data finding

The [nine-record report](real_world/REPORT.md) shows material differences with MNE-native padding even after trimming. Matched-policy numerical agreement is not a claim that different defaults are interchangeable or physiologically optimal. The three-subject convenience subset supports no population, diagnostic, motor-imagery or artifact-classification inference.
