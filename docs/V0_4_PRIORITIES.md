# Evidence-based v0.4.0 priorities

Planning and adoption improvements in review, **not a v0.4.0 release**. Published
v0.3.0 remains Research Alpha. Rank by correctness/privacy impact, then observed
first-use friction, then breadth. A future release requires owner approval.

| Priority | Evidence / unresolved risk | Next scoped work | Acceptance evidence before claiming completion |
| --- | --- | --- | --- |
| P0 gate | No independent beta/methods review exists; current executions are maintainer/CI only | Run the frozen five-person program after outreach approval; retain failed attempts | Actual five-session disposition table, task denominators, assistance records, consented aggregate feedback; never invented recruitment |
| P1 — filter interpretation | The [pilot](real_world/REPORT.md) found 10.28–25.40% native-padding waveform differences, 3.89–12.97% even after trimming | Qualified external review; explicit policy comparison and edge/transient sensitivity studies | Reviewed findings, full parameter traces, fixed tolerances and public failure cases; no silent default change or physiological-optimality claim |
| P1 — data boundaries | Current EDF decoder is a limited uniform-rate benchmark; mixed-rate/unknown-unit/huge inputs are incompletely characterized | More synthetic malformed/mixed-rate/metadata fixtures, explicit channel/unit policy and resource limits | Fixtures with expected accept/reject behavior, memory/time budgets and failure messages on declared OS/Python matrix |
| P1 — artifact validity | Gross injected bursts/flatlines and heuristic counts have no expert annotation truth | Obtain appropriately licensed annotations and qualified review before performance claims | Declared annotation protocol, retained exclusions, precision/recall uncertainty under a justified design; no classifier-quality claim from current controls |
| P2 — onboarding | Published README lacked a guided path/screenshots; bug template still said publication preparation | This PR: Quick Start, clean-install automation, screenshots, safe diagnostics and feedback forms | Actual fresh-environment and Windows/Linux CI results; beginner timing/help/comprehension still needs independent beta evidence |
| P2 — reproducibility DX | Prior walkthrough reproduced a cohort but gave no small runnable plotted lesson | This PR: one-record executable lesson, explicit units/settings/reference/hashes | Declared single-record gates and offline rerun; keep it separate from nine-case and independent-user evidence |
| P2 — estimator sensitivity | Band-edge leakage near .5 Hz and interpolation can alter power | Controlled edge-frequency/window/interpolation studies and documented conventions | Analytical/synthetic targets, sensitivity ranges and preserved disagreements across supported dependencies |
| P3 — breadth | Three convenience-selected participants and one EEG acquisition source; no real EMG | Broader licensed EEG/EMG protocols after rights/acquisition review | Dataset-specific units/reference/anti-alias evidence, fixed selection/exclusions and independent reproduction; no clinical implication |
| P3 — performance/accessibility | Synthetic allocation tracing is not process RSS; no independent accessibility evaluation | Declared workloads/RSS budgets and student keyboard/zoom sessions | Measured hardware/context, failure limits, real feedback and documented supported behavior; avoid unsupported speed claims |

First-use evidence is in [the audit](adoption/INSTALLATION_AUDIT.md). The
[beta protocol](beta/PROGRAM.md) defines proposed success criteria; it contains
no completed testers. Independent external review is a separate acceptance gate,
not replaced by another test count. v1.0 criteria remain in [ROADMAP.md](../ROADMAP.md).
