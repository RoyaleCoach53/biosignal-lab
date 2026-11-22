# Changelog

## Unreleased — proposed 0.3.0

- Preserved and critically reviewed the incoming six-record PhysioNet pilot; added official hash, independent EDF scaling, cohort, negative PSD and privacy protections.
- Added a separately predeclared nine-record EEG interoperability protocol with independent digital decoding, matched MNE filtering/PSD, band integration, channel metrics, controlled corruptions and parameter sensitivity.
- Recorded a material non-equivalence finding for MNE-native padding; numerical success is scoped to matched settings.
- Added raw/processed spectral comparison, raw channel summaries, explicit padding and software-version exports; retained processing defaults.
- Added offline regression tests, real-data/security CI, synthetic timing/allocation benchmarks, educational documentation and a staged v1.0 acceptance roadmap.
- Human recordings are not distributed; dataset attribution accompanies derived results. No clinical or independent physiological validation is claimed.
- Development changes require review and explicit merge/release approval. The published v0.2.0 release is preserved.

## 0.2.0 — 2026-11-22

First public source release, based on the recovered 27-file v0.2 archive.

### Original implementation

CSV/optional EDF import, modality separation, unit conversion, offline filters,
Welch PSD and EEG band power, spectrograms, coherence, Hjorth and EMG descriptors,
heuristic signal-quality review, Streamlit dashboard, CLI, and report exports.
The original 73-test suite was independently rerun successfully before changes.

### Verified defects fixed during publication review

- The default dashboard crashed on recordings at or below its 30-second viewport
  because a slider had equal bounds. A fixed full-recording view now handles these inputs.
- The same equal-bound problem at a 0.5-second analysis window is handled explicitly.
- Single-segment coherence could report unity for unrelated signals. At least two
  overlapping segments are now required; constant channels and undefined spectra
  produce a clear unavailable message instead of misleading values or NaNs.
- Rounding interpolation limits up could accept gaps longer than the configured
  maximum at fractional sample limits. Both processing paths now round down.
- The EEG simulator could alias a 50 Hz component into lower frequencies at low
  supported sampling rates. Tones at or above Nyquist are now omitted.
- The EDF modality test now skips correctly when the optional MNE dependency is absent.

### Publication and reproducibility

- Added 12 regression tests, including real Streamlit application runs.
- Added a 12-check executable numerical benchmark and current result JSON.
- Added two small synthetic CSV datasets with a generator and checksum manifest.
- Added Windows/Linux, Python 3.10/3.12 CI, build artifacts, and pinned action revisions.
- Declared a build backend compatible with SPDX metadata and preserved MIT notices.
- Added release, architecture, dependency, contributor, security, and provenance documentation.
- Configured local dashboard binding, a 50 MB upload cap, and disabled usage statistics.

This is an alpha research release. No clinical validation or human-data performance
claim is introduced by these changes.
