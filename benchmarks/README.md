# Reproducible numerical benchmarks

These are engineering checks on known synthetic signals, not clinical validation.
Run from a clean checkout with Python 3.10+:

```sh
python -m pip install --upgrade pip
python -m pip install -e ".[dev,all]"
python -m pytest -ra
python benchmarks/verify.py --output local-results/verification.json
```

The suite retains the original 73 tests and adds 12 release regressions. Install
both MNE and Streamlit to run all 107 tests without optional skips. The benchmark
requires MNE and records the environment rather than silently omitting its comparison.

## Twelve benchmark checks

- EEG 2, 10, 35, and 42 Hz tones: 10 µV peak, 250 Hz sampling, 60 seconds;
  theoretical power 50 µV², tolerance 3%, default pipeline filters and four-second PSD.
- EMG 200 Hz tone: 100 µV peak, 10 seconds, sampling at 500 and 2000 Hz;
  theoretical RMS 100/sqrt(2) µV, tolerance 2%, modality-specific default filters.
- Welch PSD compared to MNE after explicit unit conversion, Hann window,
  500-sample segments/FFT, 250-sample overlap, mean averaging; rtol 1e-7, atol 1e-10.
- Seeded white-noise PSD integral compared with variance, 8% relative tolerance.
- A 50 Hz notch control: post/pre PSD ratio below 0.01 at the tone bin.
- Unsupported gamma coverage returns unavailable, not zero.
- A 0.4-second interior gap is rejected under the 0.1-second default policy.
- Quality controls detect a known burst and flatline, with a clean negative control.

The script also imports and analyzes both sample CSV files, and times an
8-channel, 60-second, 250 Hz synthetic recording after one warm-up over five
repetitions. Timing is environment-specific and is not a production throughput
or speedup claim. The original report's 0.039-second timing is historical.

## Evidence

[Current results](../docs/VERIFICATION_RESULTS.json) contain settings, targets,
tolerances, measured errors, warnings, dependency versions, and pass/fail results.
CI uploads separate results for each environment. The current audit summarizes
the numerical differences and the source archive's provenance.

[Pinned Windows/Python 3.12 environment](../requirements/validation-py312-windows.txt)
records the local review environment, including audit/build tools. It is not a
universal cross-platform lock. For other platforms, resolve the package's declared
dependencies and compare numerical tolerances, not timings or bit-identical output.

The tests include generated EDF formatting, CSV timebase consistency, unit scaling,
filter attenuation, missing-gap handling, artifact controls, spectrogram localization,
and coherence controls. Shared SciPy/MNE numerical dependencies limit independence.

## Real EEG and performance benchmarks

See [the expanded protocol/report](../docs/real_world/REPORT.md), [the preserved baseline protocol](../docs/HUMAN_DATA_PILOT.md), and [the walkthrough](../examples/real_eeg_walkthrough.md). `python benchmarks/performance.py --output local-results/performance.json` records three synthetic in-memory workloads, with one warm-up, three timed/traced runs and clear allocator-peak limits. These are not process-RSS measurements or clinical benchmarks.
