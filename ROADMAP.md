# Roadmap and acceptance criteria

Current release line: **v0.3.0 Research Alpha**; the v0.2.0 release is preserved.
The real-EEG pilot was reviewed and merged in PR #4. Release publication requires
passing final checks and maintainer approval; see [release status](docs/RELEASE_STATUS.md).
No milestone is completed solely because a test counter is green.

The current adoption PR prepares onboarding, a small public EEG lesson and a
five-person beta program, not an official v0.4.0 release. See the
[evidence-ranked v0.4 priorities](docs/V0_4_PRIORITIES.md),
[installation audit](docs/adoption/INSTALLATION_AUDIT.md) and
[beta protocol](docs/beta/PROGRAM.md). Independent participants remain unassigned;
community outreach and any future release require owner approval.

| Milestone | Scope and evidence required |
| --- | --- |
| v0.3.0 | Reproducible real-EEG technical interoperability pilot, official hashes/attribution, matched MNE references, retained failures/sensitivity, regression coverage, Windows/Linux CI, reviewed PR and explicit release approval |
| v0.4.0 | Broader corrupted/mixed-rate/metadata fixtures, stronger input/resource bounds, band-edge and interpolation studies, configuration-driven analysis workflows |
| v0.5.0 | Student/researcher usability evaluation, accessible keyboard workflows, better comparison/export UI, reviewed educational tutorials |
| v0.6.0 | Declared performance/memory workloads and budgets, chunking/scaling proposals, repeatable measurements on specified hardware |
| v0.7.0 | Additional appropriately licensed datasets and acquisition systems, documented EDF/BDF/reference interoperability matrix |
| v0.8.0 | Independent qualified signal-processing/software review with public findings and responses; unresolved scientific assumptions remain visible |
| v0.9.0 | API/CLI compatibility freeze candidate, migration/deprecation policy, packaging/security release rehearsal, documentation and reproducibility audit |
| v1.0.0 | Stable research-software acceptance checklist below, reviewed evidence, and explicit maintainer approval |

## v1.0.0 acceptance checklist — not yet satisfied

- Document supported OS/Python versions and run clean-install, unit, integration,
  numerical, failure-path, and package tests on that matrix.
- Establish reproducible interoperability benchmarks across more than one
  acquisition source/dataset; preserve full protocols, exclusions and failures.
- Obtain independent qualified external review of numerical methods and data
  handling, and resolve or explicitly bound material findings.
- Define public API/CLI behavior, compatibility policy, processing metadata,
  reproducibility limits and a changelog/release process.
- Define performance and peak-memory budgets for specific workloads/hardware,
  measure them, and document out-of-memory and unsupported-input behavior.
- Complete a licensing/privacy/security review, avoid known unmitigated high-risk
  dependency findings, and establish usable reporting and maintenance policies.
- Exercise documentation/tutorials with students and researchers; address
  demonstrated usability/accessibility failures and document known limits.
- Obtain explicit approval for the stable research release after reviewing the
  acceptance evidence. Clinical validation, medical-device approval and diagnostic
  accuracy are separate matters and are not implied by v1.0.0.

## Beginner contributions

- [PSD units and resolution glossary — #1](https://github.com/RoyaleCoach53/biosignal-lab/issues/1)
- [Keyboard walkthrough — #2](https://github.com/RoyaleCoach53/biosignal-lab/issues/2)
- [Synthetic CSV units tutorial — #3](https://github.com/RoyaleCoach53/biosignal-lab/issues/3)

Each issue has a small scope, acceptance criteria and an offline synthetic start.
Further scientific work should prioritize an acquisition/reference audit and
independent annotations before any artifact-performance or physiological claim.
