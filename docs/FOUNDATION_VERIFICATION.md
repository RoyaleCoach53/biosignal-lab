# Foundation verification record

Executed on Linux x86_64 / Python 3.12.14 against the foundation worktree, based on
PR #6 at `e740502d1be013647bf4ec7e0233c1f65b795c97` plus the accompanying changes.
These are software-development results, not independent scientific or user studies.

- `PYTHONPATH="$PWD/src" python -m pytest -ra`: **141 passed, no skips**.
- `python benchmarks/verify.py --output <new-path>`: **12/12 numerical checks**.
- Critical Ruff checks, compilation, and local documentation links: passed;
  **159 links, zero broken** at this workstream checkpoint.
- Fresh wheel and source-distribution build: passed. Archive integrity verification
  emitted SHA256SUMS and a CycloneDX dependency inventory.
- `tools/check_installation.py`: passed in a genuinely new outside-checkout virtual
  environment. A newly built wheel was installed noneditably, imports resolved
  inside that environment, dependencies were consistent, both sample modalities
  exported reports, and Streamlit AppTest rendered synthetic data without errors.
- The source checkout was intentionally not installed into the clean audit via an
  editable link. Inherited `PYTHONPATH`/`PYTHONHOME` were stripped for subprocesses.
- Windows/macOS and hosted GitHub CI: **not executed locally**. CI matrices now
  request those platforms; their success must be observed separately.
- PyPI project, Trusted Publisher configuration, GitHub environment protection,
  independent review, and publication: **not performed**.

Generated detailed reports remain in ignored `local-results/`. The existing
release and human-data evidence under `docs/` was preserved. Build hashes are
specific to each actual artifact and should be generated after the final combined
source changes, rather than copying hashes from this earlier worktree build.
