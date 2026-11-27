# Platform acceptance ledger

This ledger follows the expanded development request. It does not rewrite the
historical release evidence or declare a stable release. The published version
remains v0.3.0 until a separately reviewed release is approved.

An implementation exists only when callable code is present. A local test result
is not a remote CI result, external review, a user study or a physical experiment.
The [development checkpoint](DEVELOPMENT_STATE.md) records current-run evidence.

| Milestone | Measurable engineering gate | External or remaining gate |
| --- | --- | --- |
| v0.4 Foundation | Reproduce inherited tests; immutable prior reports; reject stale audit output; isolated wheel install; verify artifact hashes and metadata; scan publication paths case-insensitively | Review PR #6 and integration; Windows/Linux/macOS CI; refresh dependency advisories and license review; approved release publication |
| v0.5 Engine | Unit-preserving validated signals; analytical filter/PSD/epoch/reference checks; malformed-input tests; documented supported format matrix | Methods review and independent reference implementations; broader modalities and file variants cannot be claimed from EEG tests |
| v0.6 Live | Deterministic simulator; chunk-invariant causal filters; bounded thread-safe buffer; timestamps, loss/overflow handling; actual measured workload | Physical board, amplifier and acquisition clock validation; reconnection and supported device protocols on hardware |
| v0.7 AI | Subject-disjoint evaluation; training-only preprocessing; reproducible seeds and manifests; safe model loading; actual measured metrics | Licensed task-specific datasets, independent held-out cohorts; neural architecture/deployment verification; physiological task evidence |
| v0.8 Studio | Executable typed DAG; invalid edge/cycle rejection; reproducible JSON and provenance; real connected nodes; bounded execution | Complete visual editor interaction/accessibility matrix, plugin compatibility/security review, user testing |
| v0.9 Validation | Preserve numerical disagreements; independent protocols; reproducibility package; all required failures visible | Target >100 EEG participants / >1,000 recordings, multiple EEG/EMG datasets, independent researchers and real learners; none may be invented |
| v1.0 Stable research | All mandatory subsystem gates, API compatibility policy, package/security rehearsal, complete support matrix and no critical unresolved defects | Maintainer review/approval; external requirements above; no diagnostic or medical-device claims |

## Hardware verification protocol

For each exact board/firmware/adapter/OS, declare channel labels, physical units,
reference, gain, sample format, nominal clock and packet sequence semantics before
testing. Use a calibrated source or loopback appropriate to the device, never a
human-connected electrical test without qualified supervision. Measure clock
drift, amplitude and frequency error, signal saturation, dropped packets,
disconnect/reconnect behavior, sustained channel/sample workload and latency.
Preserve failures and test conditions. A simulated adapter test satisfies none
of the electrical calibration or physical compatibility gates.

## Independent reproduction protocol

Provide the exact source SHA, clean environment instructions, dependency versions,
hash-pinned input manifests and protocol before inspecting outcomes. Have a
qualified researcher execute both analytical and recorded-signal comparisons.
Ask them to examine shared SciPy dependencies, filter padding, unit conversion,
reference/montage metadata, segment boundaries, exclusions and uncertainty.
Record reviewer consent, scope, findings and responses without inventing reviewer
identity, endorsement or peer-review status. External review is not performed by
this implementation session.

## User evaluation protocol

Recruit consenting learners/researchers separately; do not create fictional
sessions. Ask participants to install, reproduce a synthetic analysis, identify
units and limitations, construct a workflow, recover a saved project and export a
report. Measure task success, errors and time with accessible alternatives; do
not record biomedical data or personal identifiers in the repository. A local
browser automation run establishes software behavior, not human usability.

## Dataset expansion protocol

Freeze source/version/license, inclusion/exclusion, subject/session grouping,
sampling/reference/unit interpretation and outcome tolerances before analysis.
Keep recordings outside Git. Verify official hashes where available. Report
requested, included, excluded, failed and missing records separately. Classification
splits must isolate subjects and fit transforms within training folds. Broader
participant and recording counts are targets until actual licensed runs occur.

## Padding disagreement remains visible

The preserved [v0.3 report](real_world/REPORT.md) measured 10.28–25.40% waveform
relative L2 differences under native MNE padding, and 3.89–12.97% after five-second
edge trimming. Matched-policy agreement is a different experiment. A 0.1 Hz
high-pass can have long transients; five seconds is not a universal washout.
New filter APIs must state direction, state initialization and edge policy.
No comparison can establish physiological correctness merely by sharing a
numerical implementation or relaxing a tolerance.
