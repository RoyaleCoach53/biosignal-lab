Historical v0.2 release record. Relative links adjusted for this archive; exact original is preserved at the v0.2.0 tag.

# Release scientific and engineering verification â€” v0.2.0

Review date: 2026-11-22. Assessment: numerical engineering verification on
synthetic data, with AI-assisted source review. **Not clinical validation or
independent external scientific peer review.**

## Provenance and original baseline

The 27-file user-provided original ZIP has SHA-256
`f4c770952ed9570dc41cdab2ffb44fb160662c777ee742b1f7c5ed6f9686632c`.
ZIP integrity was checked before extraction; no path traversal or symbolic-link
entries were accepted. The unmodified archive was installed in a fresh virtual
environment, including MNE. Its original suite passed **73/73 tests, with zero
skips**. Original audit artifacts remain unchanged in [archive](README.md).

## Release review findings and fixes

The original numerical suite did not exercise the complete dashboard. Streamlit
AppTest reproduced a default-screen exception caused by a zero-range viewport
slider. Further regression controls demonstrated invalid single-segment coherence,
undefined coherence for constant signals, rounding up an interpolation gap limit,
and a simulator aliasing a 50 Hz tone at low sampling rates.

The release fixes these defects and adds 12 regression cases, including dashboard
EEG at 10, 30, and 60 seconds, EMG, and a 0.5-second recording. After the fixes,
**85 tests passed, zero failed, zero skipped** locally. The new regression suite
initially failed on the reproducible defects before those fixes were applied.
See [changelog](../../CHANGELOG.md) and [architecture review](../ARCHITECTURE.md).

## Reproduced numerical measurements

| Synthetic case | Analytical target | Measured | Error |
| --- | --- | --- | --- |
| EEG 2 Hz, 10 ÂµV peak | 50 ÂµVÂ² delta | 50.0034405 ÂµVÂ² | +0.006881% |
| EEG 10 Hz, 10 ÂµV peak | 50 ÂµVÂ² alpha | 49.9937626 ÂµVÂ² | âˆ’0.012475% |
| EEG 35 Hz, 10 ÂµV peak | 50 ÂµVÂ² gamma | 49.7593375 ÂµVÂ² | âˆ’0.481325% |
| EEG 42 Hz, 10 ÂµV peak | 50 ÂµVÂ² gamma | 49.0298870 ÂµVÂ² | âˆ’1.940226% |
| EMG 200 Hz, 100 ÂµV peak, fs=500 | 70.7106781 ÂµV RMS | 70.71580 ÂµV | +0.007243% |
| EMG 200 Hz, 100 ÂµV peak, fs=2000 | 70.7106781 ÂµV RMS | 70.70170 ÂµV | âˆ’0.012697% |

EEG tone cases use 60 seconds at 250 Hz, default filters, and four-second Welch
segments. EMG tone cases use 10 seconds and modality-specific default filters.
Acceptances were 3% power error for EEG and 2% RMS error for EMG. Differences are
consistent with the selected filter and estimator; the tests do not measure
physiological ground truth. The low-rate EMG case emits a bandwidth warning.

The executable benchmark passes **12/12 checks**. Additional controls include:

- MNE/SciPy Welch comparison: max absolute difference
  **7.1054e-14 ÂµVÂ²/Hz**, with matched units, Hann window, overlap, FFT and averaging.
- White-noise integrated PSD: **24.8875461 ÂµVÂ²**, versus variance **24.9580208 ÂµVÂ²**
  (8% relative tolerance).
- 50 Hz notch residual/pre-filter PSD ratio: **9.05565e-6** (limit 0.01).
- At 80 Hz sampling, gamma coverage is 2/3 and its power is unavailable, not zero.
- A 0.4-second missing interval is rejected under the default 0.1-second policy.
- Synthetic quality controls: one burst flag, two flatline flags, no clean-control flags.

The suite separately checks CSV sample-rate mismatch, irregular timestamps,
boundary gaps, unit scaling, real-format synthetic EDF decoding and modality
selection, Hjorth parameters, time-frequency localization, and coherence controls.

## Reproducibility

```sh
python -m pip install --upgrade pip
python -m pip install -e ".[dev,all]"
python -m pytest -ra
python benchmarks/verify.py --output local-results/verification.json
```

The recorded Windows/Python 3.12.14 environment used NumPy 2.5.5, SciPy 1.18.1,
pandas 2.3.3, MNE 1.13.2, Streamlit 1.67.0, and Plotly 6.9.0. Exact installed
versions are captured in the [environment snapshot](../../requirements/validation-py312-windows.txt).
The [result JSON](VERIFICATION_RESULTS_v0.2_release.json) includes parameters, warnings, and
five local timing repetitions after warm-up. Timing is not a throughput guarantee
or a comparison with the original environment. CI publishes per-environment results.

## Security and license review scope

The recovered implementation, tests, dashboard, build configuration, and new
release files were inspected. No credential-pattern matches, unnecessary personal
contact information, or unrelated private-project code were found. HTML labels
are escaped; no remote analysis API or credential is needed. MIT notices were
preserved. Installed dependencies were checked for known advisories, with the
local project reviewed separately; see [dependency review](../DEPENDENCIES.md).
This is not a penetration test or a guarantee against unknown vulnerabilities.

## What this evidence does not establish

No independent human recording dataset, clinical labels, diagnostic performance,
artifact sensitivity/specificity, device calibration, physiological validity,
statistical reliability of coherence, or regulatory status was evaluated.
SciPy/MNE comparisons may share numerical code. Missing data, reference choices,
filter transients, acquisition bandwidth, and band-edge leakage remain material
limitations. See [METHODS.md](../METHODS.md) and [LIMITATIONS.md](../LIMITATIONS.md).

Recommended next work is a frozen protocol on an appropriately licensed human
dataset and review by external signal-processing researchers. No clinical claim
follows from this publication.
