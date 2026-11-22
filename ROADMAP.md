# Roadmap

## Released in v0.2.0

Local CSV/optional EDF analysis, EEG/EMG defaults, spectral and descriptive metrics,
Streamlit dashboard, CLI and reports, synthetic samples, reproduced original tests,
release regressions, executable benchmarks, CI, and provenance records.

## Next: independent research evidence

1. Freeze a task-specific protocol and evaluate an appropriately licensed public
   human dataset. Record channel typing, references, preprocessing, and exclusions.
2. Compare measurements with matched-setting reference tools and publish failures.
3. Obtain independent annotations before reporting artifact detection sensitivity,
   precision, confidence intervals, or cross-subject generalization.
4. Request review from signal-processing and biomedical engineering researchers.

## Usability and engineering

- Raw-versus-processed PSD and line-noise comparisons.
- Better acquisition/reference metadata, EDF variant coverage, and BIDS-style exports.
- Explicit CLI controls to disable each filter and load a configuration file.
- Streaming/chunked analysis and documented memory/resource budgets.
- Additional accessibility checks and educational notebooks on leakage and aliasing.

## Genuine adoption

Publish a short reproducible tutorial, ask a few students and laboratories to try
one concrete workflow, turn their friction into focused issues, and review small
contributions promptly. Track independently reproduced results and solved user
problems alongside repository activity. Avoid unsupported impact or clinical claims.

No medical diagnostics or safety-critical control is planned. Dates, external
program acceptance, grants, and community interest are not guaranteed.
