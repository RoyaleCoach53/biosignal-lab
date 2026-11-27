# Installation and first-use audit

Maintainer engineering audit, 2026-11-23. **Not independent adoption, a fresh-OS
study, learner timing or a clinical evaluation.** No beta participant is counted.

## Published v0.3.0, freshly installed

Cloned the public annotated v0.3.0 tag at
`bff6d67adfbba1d8ef35fdb80acc21284c5683f6` into a new directory. Created a
separate CPython 3.12.14 virtual environment with no system/user-site packages;
its initial package list contained only pip 25.0.1. Upgraded pip and installed
`.[app]` noneditably with `--no-cache-dir`, resolving packages from the registry.
This audits a source-wheel installation, not the README's editable variation.

Actual outcomes in [RELEASE_INSTALL_AUDIT.json](RELEASE_INSTALL_AUDIT.json):

- Runtime imports came from isolated `site-packages`; version 0.3.0.
- `pip check` passed. MNE and pytest were absent, as expected for the app extra.
- Both included synthetic EEG/EMG CSVs produced correctly versioned JSON and HTML.
- Streamlit AppTest rendered the default dashboard without exceptions.
- A real localhost browser showed the synthetic controls, raw/processed spectrum,
  units and warnings; [screenshots](../SCREENSHOTS.md) retain that evidence.
- A separate point-in-time [advisory audit](CLEAN_DEPENDENCY_AUDIT.json) checked
  38 installed distributions and found zero known vulnerability entries. The local
  BioSignal distribution was absent from the advisory database and reviewed as
  source instead; this does not certify unknown defects or historical versions.

An earlier preparatory environment targeted the working checkout, was cancelled
and is excluded. Downloads on this connection took multiple minutes. No claim is
made that first installation takes five minutes. Prerequisite Python/Git were
already on the Windows host; this does not test installing those prerequisites.

## Findings and candidate changes

| Observation | Response in the adoption branch | Verification / remaining limit |
| --- | --- | --- |
| No guided short exercise or screenshots | Five-minute **post-install** exercise, actual synthetic screenshots and unit/warning explanations | Maintainer executed; independent learner comprehension/timing remains unmeasured |
| Activation/PATH ambiguity in source instructions | Explicit virtual-environment Python commands and `python -m streamlit` | Windows executed; Linux first-use CI proposed; macOS remains exploratory |
| Repeated deprecated `use_container_width` messages on Streamlit 1.67.0 | Capability-based current stretch API, fallback for older signatures; descriptions where supported | Candidate AppTest passed with those warning messages absent; compatibility controls cover signatures, not an installation of every historical Streamlit version |
| Problem template still referred to publication preparation | Updated alpha status, safe environment/reproduction/feedback templates | Forms reviewed; actual submission/rendering awaits default-branch merge, not claimed tested by posting an issue |
| Cohort reproduction lacked a small plotted lesson | One-record checksum-pinned EDF/MNE lesson with fixed settings, hashes and derived PSD/band figure | Maintainer run and offline rerun; real-data CI exercises it without committing EDFs |

The width change follows the current official [Streamlit dataframe API](https://docs.streamlit.io/develop/api-reference/data/st.dataframe)
and [design guidance](https://docs.streamlit.io/develop/concepts/design/best-practices).
No full accessibility compliance claim follows from adding descriptions.

The new `tools/check_installation.py` repeats clean installation in a **new,
outside-checkout** virtual environment, refuses existing environments, avoids pip
cache reuse, checks isolation/dependencies, runs packaged EEG/EMG CLI exports and
AppTest, and exports redacted software facts. It does not clear directories or
collect recordings. Run with `--venv ../new-audit-env --output local-results/install.json`.

Windows/Linux Python 3.12 first-use jobs are added alongside the existing
Windows/Linux Python 3.10/3.12 regression matrix. The PR's Checks view and artifacts
are authoritative for the actual candidate CI outcome; this source document does
not predeclare those jobs successful. The immutable release audit above is one
maintainer execution, not five testers. See [beta criteria](../beta/PROGRAM.md)
and [priorities](../V0_4_PRIORITIES.md).
