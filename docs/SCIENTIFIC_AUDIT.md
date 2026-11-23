# Scientific/software review — proposed v0.3.0

This development candidate is not released or merged. The published v0.2.0 tag
and source remain unchanged. Historical v0.2 release evidence is preserved in
[the archived audit](archive/SCIENTIFIC_AUDIT_v0.2_release.md) and
[measurements](archive/VERIFICATION_RESULTS_v0.2_release.json).

## Actual evidence

- The original 73-test archive baseline was previously reproduced before v0.2 fixes.
- Current development suite: **107 passed, 0 failed, 0 skipped** locally.
- Synthetic mathematical benchmark: **12/12 checks passed**.
- Existing six-record no-filter baseline: **6/6 passed**, now with official hashes
  and independent EDF scaling checks.
- Expanded pilot: **9/9 passed**, 64 channels each, three subjects/three conditions,
  first 60 seconds, 160 Hz. No post-hoc exclusions.
- Raw and filtered PSD, waveform, band powers and channel metrics agree with
  explicitly configured references within the predeclared tolerances.
- Different MNE-native padding produces material disagreement; it is documented,
  not hidden behind the matched-policy pass.
- Synthetic performance/allocation measurements cover three declared workloads;
  traced allocation peaks are not process RSS or a cross-machine speed claim.

Read [the real-data report](real_world/REPORT.md), [baseline protocol](HUMAN_DATA_PILOT.md),
[results](real_world/results.json), [performance](real_world/performance.json),
[methods](METHODS.md) and [limitations](LIMITATIONS.md).

## Security and source boundaries

Human recordings remain outside the repository and are checked against official
hashes before decoding. Reports contain derived summaries and attribution, not
waveforms or personal headers. Automated publication checks reject recording
formats, unapproved CSVs and common credential patterns. Dependency advisories,
clean packaging and CI are checked for the PR, with evidence in its Checks view.
No unrelated private-project code is used.

This is an AI-assisted engineering review, not independent external peer review,
clinical validation, device calibration or evidence of diagnostic usefulness.
See [the v1.0 acceptance roadmap](../ROADMAP.md) for work still required.
