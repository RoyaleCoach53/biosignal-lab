# Release validation record

Review date: 2026-11-22. Version: 0.2.0, alpha research software.

The original source has been recovered and integrated. The original audit and
verification JSON are preserved in `docs/archive/`; per-file archive hashes are
recorded in `SOURCE_PROVENANCE.json`.

| Check | Recorded local result |
| --- | --- |
| Original archive suite before changes | 73 passed, 0 failed, 0 skipped |
| Release suite with regression tests | 85 passed, 0 failed, 0 skipped |
| Executable numerical benchmark | 12/12 passed |
| Application paths | EEG 10/30/60 s, EMG default, and 0.5 s input exercised with Streamlit AppTest |
| Source compilation and critical Python lint | Passed |
| Dependency consistency | `pip check` passed |
| Installed environment advisory audit | No known vulnerabilities after updating environment pip; local project checked separately |
| Source provenance/security inspection | Original and newly published files reviewed; no detected credential patterns or unrelated private-project code |
| Clinical or independent human-data validation | Not performed |

CI runs Linux and Windows with Python 3.10 and 3.12 and uploads its own results.
The [Actions page](https://github.com/RoyaleCoach53/biosignal-lab/actions) and
[release page](https://github.com/RoyaleCoach53/biosignal-lab/releases) are the
authoritative public records of workflow and publication state.

Read [SCIENTIFIC_AUDIT.md](SCIENTIFIC_AUDIT.md), [DEPENDENCIES.md](DEPENDENCIES.md),
and [CHANGELOG.md](../CHANGELOG.md) for the evidence, scope, and fixes.
