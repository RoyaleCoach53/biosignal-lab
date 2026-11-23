# Release status — v0.3.0 Research Alpha

Version metadata: **0.3.0**. Scope: real-EEG technical interoperability and
reproducible research/education workflows. This is alpha software, not a stable
v1.0 platform or a clinically validated system.

The pilot was reviewed and merged in [PR #4](https://github.com/RoyaleCoach53/biosignal-lab/pull/4).
Its source history and the public v0.2.0 tag/release are preserved. The owner
authorized v0.3.0 publication on 2026-11-23, conditional on final release checks.
The [GitHub release page](https://github.com/RoyaleCoach53/biosignal-lab/releases/tag/v0.3.0)
is authoritative for publication status; version metadata alone does not publish a release.

## Release gates

- 107 automated tests without failures or optional skips; 12 synthetic numerical checks.
- Six full-recording baseline and nine expanded EEG cases, official SHA-256 verified,
  with no post-hoc exclusions and unchanged protocol/tolerances.
- Matching version metadata, finite result JSON, valid local documentation links,
  critical lint/compilation and source/wheel builds.
- No raw human recordings or credentials in tracked files, distributions or assets;
  dependency consistency and known-advisory checks.
- Green Windows/Linux, Python 3.10/3.12 CI plus real-data/security and documentation
  workflows on the final commit; an annotated v0.3.0 tag pointing to that commit.
- Package installation and CLI/API smoke checks; final asset hashes verified before
  publishing the GitHub Release as **Research Alpha / pre-release**.

Recorded local release checks are in [the verification record](RELEASE_VERIFICATION_v0.3.0.json).
Exact final-commit CI links and asset checksums accompany the GitHub Release,
avoiding a self-referential commit hash in the source evidence.

See [release notes](RELEASE_NOTES_v0.3.0.md), [the scientific report](real_world/REPORT.md)
and [limitations](LIMITATIONS.md). MNE-native padding differences remain material;
shared numerical routines, three participants, unvalidated artifact flags and lack
of real EMG or external qualified review limit the evidence. Clinical validation
and independent physiological truth are not established. v1.0 criteria remain open
in [the roadmap](../ROADMAP.md); publishing v0.3.0 does not start the next milestone.
