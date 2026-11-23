# Development and release status

Current public release: **v0.2.0 Research Alpha**, preserved unchanged.
Candidate: **0.3.0.dev0**, proposed real-data interoperability pilot.

The development branch integrates and preserves the existing
`research/physionet-human-data-pilot` history. Proposed changes are submitted in
a PR for review. Main-branch merging and new releases require explicit approval.

Local checks: 107 tests passed without skips/failures, 12 synthetic checks passed,
six baseline recordings passed, and nine expanded real-EEG records passed.
The [report](real_world/REPORT.md) documents numerical errors, padding disagreement,
controlled corruptions, data terms and limits. CI produces separate per-environment
evidence; the PR's Checks view is authoritative for the latest commit.

No clinical validation or independent external physiological review is established.
v1.0 acceptance criteria remain open in [ROADMAP.md](../ROADMAP.md).
