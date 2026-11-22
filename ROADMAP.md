# Roadmap

This roadmap describes intended work, not completed implementation or guaranteed dates.

## 1. Recover and verify v0.2

- Recover the original source archive, audit report, and verification JSON.
- Record checksums and inspect every file before execution or publication.
- Establish a clean environment and reproduce the available test suite.
- Review architecture, parsers, units, filters, dependency licenses, and security.
- Reproduce numerical regressions using the protocol in `benchmarks/README.md`.
- Publish only results tied to a verified commit and environment.

## 2. Make the release usable

- Verify installation and actual application commands on supported platforms.
- Add a compact walkthrough and properly licensed synthetic sample data.
- Run implementation tests in GitHub Actions and publish the exact results.
- Add reproducible benchmark scripts and machine-readable output.
- Create v0.2.0 only after the release gates are met.

## 3. Build independent evidence

- Ask biomedical engineering and signal processing reviewers to examine assumptions.
- Compare calculations with a reference implementation using matched settings.
- Evaluate explicitly defined tasks on appropriately licensed public recordings.
- Report failure cases and uncertainty alongside successful examples.
- Evaluate artifact flags against annotations before making performance claims.

## 4. Support adoption

- Publish a short tutorial with a reproducible input and a useful interpretation.
- Invite a few students and researchers to try a concrete workflow and report friction.
- Label small issues with clear acceptance criteria and review contributions promptly.
- Track reproducibility, resolved user problems, and useful contributions.
- Maintain a changelog, support policy, and documented release process.

Community interest, grants, and third-party program acceptance are external
outcomes. They are not guaranteed by public hosting or a release tag.
