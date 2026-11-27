# BioSignal Lab: a local-first platform for auditable signal-processing research

Manuscript working draft. This document has not been submitted, peer reviewed or
accepted. Authorship and contribution statements require contributor agreement.
It describes software and the evidence scope rather than announcing a release.

## Abstract

BioSignal Lab is an MIT-licensed Python toolkit for local EEG/EMG inspection,
signal-quality summaries and reproducible analysis reports. The existing v0.3.0
pipeline combines explicit input units, bounded missing-data interpolation,
offline filtering, spectral estimation and exportable processing metadata. The
development integration extends this base with separate processing, acquisition,
grouped-learning and workflow interfaces while retaining legacy behavior. The
starting environment reproduced 107 tests and 12 analytical/numerical checks.
These outcomes establish specific software properties. They do not establish
physiological validity, artifact sensitivity, diagnostic accuracy or hardware
compatibility. A previously recorded nine-recording EEG interoperability pilot
is preserved with its limitations and padding-policy disagreements.

## Motivation and design

Small research tools can obscure physical units, preprocessing assumptions,
training/test separation and version provenance behind interactive interfaces.
The platform therefore keeps core processing local, offers deterministic
synthetic examples and treats exported parameters as part of the result. Core
analysis requires no remote account or API key. Optional dependencies support
specialist methods; unsupported capabilities must remain visibly unavailable.

The validated legacy container represents channels by samples in microvolts.
The new processing layer uses a separate unit-aware signal abstraction so that
non-voltage measurements cannot silently acquire voltage semantics. Acquisition,
machine learning and workflow orchestration are separate modules, permitting
failure-path testing without a connected device or a human dataset.

## Numerical methods and verification

The released EEG/EMG path uses explicit sampling frequency, mean removal,
Butterworth/notch preprocessing and Hann-window Welch power spectral density.
Reports record processing parameters, units and software versions. Analytical
tones, controlled gaps, known artifacts and generated EDF records exercise the
numerical and parsing paths. These tests should be supplemented by independent
implementations and boundary-condition studies when new methods are introduced.

The preserved interoperability case study used three participants and nine
PhysioNet EEG Motor Movement/Imagery Dataset recordings, with checksum-pinned
input, declared settings and no post-hoc exclusions. It compared a separate
limited EDF digital decoder, explicitly configured MNE processing and separately
implemented band integration. MNE and BioSignal Lab share SciPy routines, limiting
reference independence. The [original report](real_world/REPORT.md) is the
authoritative source of the prior measurements and attribution; those historical
runs were not rerun during the baseline environment setup.

Native MNE and BioSignal Lab padding produced material waveform differences that
remain documented. Numerical agreement under a matched edge policy must not be
generalized to equivalence under different policies. Long high-pass transients
also limit simplistic edge trimming.

## Reproducibility, privacy and security

Frozen experiment definitions should identify source SHA, dependency versions,
input hashes, units, sampling rates, random seeds, evaluation grouping and
processing parameters. Immutable report/version paths preserve prior evidence.
Model and workflow interchange should use bounded validated data formats rather
than executable deserialization. Third-party plugins are executable code and
require explicit trust; discovery alone must never execute them.

Human recordings are not packaged or committed. Public demonstrations use
synthetic signals. Project metadata can still contain sensitive names and must
be reviewed before sharing. Dataset licenses remain separate from the software
license. Dependency inventories and advisory scans are point-in-time evidence,
not guarantees of security.

## Evaluation and limitations

The baseline run used Linux and Python 3.12.14 and passed 107 tests without skips,
12 numerical benchmark checks, package builds and local dashboard readiness
checks. These are local results; the integration's actual subsystem test counts
and measurements belong in its checkpoint and generated reports after execution.
No cross-platform CI, new real-data cohort, clinical experiment, physical device,
independent scientist or real user session is implied by these counts.

The expanded platform requires further methodological review, device testing,
task-specific machine-learning evaluation and accessibility/user studies. Deep
learning architectures, export targets and file formats should be listed only
where implemented and verified. Stable v1.0 acceptance remains governed by the
[milestone ledger](PLATFORM_ACCEPTANCE.md).

## Availability and citation

Source and existing releases: <https://github.com/RoyaleCoach53/biosignal-lab>.
Use the exact version and commit in scientific work, cite the original dataset
and numerical libraries, and retain their licenses and method references.
Machine-readable software citation metadata is in `CITATION.cff`. This project
does not claim a DOI, journal publication, institutional endorsement or external
peer review for this draft.
