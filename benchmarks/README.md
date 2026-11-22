# Reproducible benchmark protocol

No executable benchmark or verified result is available in this checkout yet.
The historical verification JSON must be recovered and reproduced before any
historical value is described as verified.

## Required numerical cases

| Case | Input and expected check |
| --- | --- |
| EEG-like reference tones | Separate 2, 10, 35, and 42 Hz sine waves, peak amplitude 10 microvolts; compare unfiltered mean-square power with the analytical 50 microvolts squared target |
| EMG-like reference tone | 200 Hz sine wave, peak amplitude 100 microvolts, sampling rate comfortably above Nyquist; compare unfiltered RMS with 100/sqrt(2) microvolts |
| Filter regressions | Measure actual filter gain at each tone; compare processed measurements with the expected filtered response and report edge treatment |
| Spectral consistency | Match all Welch settings and units with a reference implementation; compare PSD arrays and integrated power |
| Sampling-rate handling | Reject invalid rates and unsupported ranges; verify boundaries and unavailable outputs |
| Timestamp and import handling | Test rate mismatch, duplicates, mixed channel types, unit conversion, and synthetic valid EDF input if supported |
| Missing data | Exercise short gaps, long gaps, nonfinite values, and insufficient recording length |
| Quality flags | Test known synthetic disturbances and clean negative controls; document thresholds and failure cases |

These ideal tones are mathematical fixtures, not realistic EEG or EMG recordings.
For exact unfiltered RMS targets, use integer-cycle durations. For spectral and
filtered checks, predeclare sample rate, duration, phase, window, padding, edge
exclusion, integration rule, and tolerances before inspecting outcomes.

## Reproduction record

Publish a command that runs on a clean checkout, the dependency lock or exact
environment, deterministic seeds where relevant, input provenance and hashes,
machine-readable measured values, comparison targets, tolerances, and exit status.
Record the full collected and passed/failed/skipped test counts.

Timing results should include hardware, operating system, warm-up policy, input
size, number of repetitions, and summary statistics. Do not compare runtimes
under different workloads or claim a speedup without measured evidence.

Application-specific commands will be added after source recovery; none are
invented here. This protocol is newly prepared and is not the original audit report.
