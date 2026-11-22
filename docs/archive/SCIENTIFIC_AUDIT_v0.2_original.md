# BioSignal Lab — Scientific Verification Record

**Version:** 0.2.0  
**Assessment:** engineering/numerical verification; NOT clinical validation  
**Independent clinical dataset evaluation:** NOT PERFORMED  
**Intended use:** educational and exploratory signal analysis only.

## Verified calculations

| Operation | Mathematical expectation | Result | Status |
|---|---|---|---|
| 10 µV peak sine at 2 Hz | Delta power 50.000 µV² | 50.003 µV² (+0.007%) | Pass |
| 10 µV peak sine at 10 Hz | Alpha power 50.000 µV² | 49.994 µV² (−0.012%) | Pass |
| 10 µV peak sine at 35 Hz | Gamma power 50.000 µV² | 49.759 µV² (−0.481%) | Pass |
| 10 µV peak sine at 42 Hz | Gamma power 50.000 µV² | 49.030 µV² (−1.940%) | Pass |
| 100 µV peak sine at 200 Hz | EMG RMS 70.7107 µV | 70.7158 µV | Pass |
| White-noise PSD integration | PSD integral ≈variance | Tolerance-tested | Pass |
| Welch PSD cross-check | Agrees with MNE for matched Hann/overlap and units | Max absolute difference 4.26×10⁻¹⁴ µV²/Hz | Pass |
| Hjorth mobility 10 Hz sine | ≈2π×10 s⁻¹ | Within numerical tolerance | Pass |
| Uncorrelated vs identical channels | Low average vs unity coherence | Controls tested | Pass |
| Synthetic mixed EEG/EMG EDF | Correct selection and µV units | EDF file decoded | Pass |
| Wrong CSV sample rate | Reject timebase mismatch | Rejected | Pass |
| Long missing segment | No silent interpolation | Rejected | Pass |
| Unobservable band above Nyquist | Unavailable/null, not zero | Corrected | Pass |

## Testing summary

**73 automated tests passed, 0 failed**, with MNE installed for the independent reference and EDF tests. Example 8-channel, 60-second synthetic EEG (250 Hz) processed in 0.039 seconds on the current test environment; this is a local benchmark, not a production throughput guarantee. Machine-readable results: `docs/VERIFICATION_RESULTS.json`.

## Critical findings corrected from v0.1

1. **EEG gamma attenuation:** the previous default 40 Hz lowpass attenuated 35 and 42 Hz tones despite reporting gamma to 45 Hz. v0.2 no longer applies a default EEG lowpass.
2. **EMG high-frequency attenuation:** the previous default 150 Hz lowpass reduced the RMS of a 200 Hz, 100 µV peak sine to ~1.30 µV instead of ~70.71 µV. The new defaults preserve it while warning when the sampling rate cannot support full sEMG bandwidth.
3. **Partial Nyquist coverage:** unobservable EEG bands and mains-frequency fractions now return null instead of an incorrect zero.
4. **CSV sampling-rate mismatch:** declared sampling rate and time column are now checked against each other.
5. **Modality mixing:** EDF reader selects EEG and EMG separately using inferred channel labels, instead of silently treating both as one signal modality.
6. **Missing-data fabrication:** interior interpolation now has a maximum 100 ms contiguous gap by default; boundary gaps and longer gaps are rejected.
7. **PSD near lower delta boundary:** increased default EEG spectral window to 4 s; delta power close to 0.5 Hz remains sensitive to band-edge truncation, and this limitation is explicitly documented.
8. **Artifact timing:** PSD and artifact windows are decoupled (4 s vs 1 s by default), avoiding unnecessarily broad review intervals.
9. **Residual mains-interference reporting:** metrics now distinguish unobservable mains bands from measured low post-notch residual values.

## Acceptance boundaries

**Passed:** basic DSP formula consistency; independent PSD agreement with MNE; known synthetic periodic/noise signals; generated EDF format and channel/unit decoding; coherent error handling; security-oriented no-clinical-claim reports.

**Not passed/not attempted:** validation on independently collected EEG/EMG recordings; dataset-level benchmark; annotated blink/EMG artifact detection sensitivity or specificity; hardware accuracy; physiological ground truth; clinical performance or regulatory status.

A code passing automated tests does not establish that it works on all patients, electrodes, references, or acquisition systems. No results here justify diagnostic labeling.

## Reproducibility

```bash
python -m pip install -e '.[dev,edf]'
pytest -q
```

See `tests/test_scientific_validation.py` for individual ground-truth tests and `docs/METHODS.md` for definitions and references. Optional EDF/MNE tests skip if MNE is not installed. Do not package public EEG datasets with the source without checking dataset terms.

## Required next independent scientific study

1. Obtain an appropriately licensed dataset: e.g. PhysioNet EEG Motor Movement/Imagery (64 channels, 160 Hz) and optionally Sleep-EDF Expanded (mixed PSG modalities).
2. Create a frozen experimental protocol: subject list, EDF channels, sampling rate, filtering, artifact policy, window length and definitions of metrics.
3. Verify conversion to µV and compare per-channel PSD and band powers against MNE with identical settings.
4. Assess cross-session reproducibility, missing/flat signal detection, and signal recording reference effects.
5. For any new artifact classifier, obtain independently annotated labels, compute event/sample sensitivity and precision with confidence intervals and use a held-out subject test split.
6. Publish anonymized numerical reports, dataset citations, software/environment versions and protocol, without including private patient recordings.

**Conclusion:** v0.2.0 is numerically checked for an educational research-tool alpha. It is **not** independently validated for scientific inference on human datasets or medically validated.
