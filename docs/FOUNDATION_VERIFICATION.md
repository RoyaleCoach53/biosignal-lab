# Foundation verification record

Executed on Linux x86_64 / Python 3.12.14 against the foundation worktree, based on
PR #6 at `e740502d1be013647bf4ec7e0233c1f65b795c97` plus the accompanying changes.
These are software-development results, not independent scientific or user studies.

- `PYTHONPATH="$PWD/src" python -m pytest -ra`: **142 passed, no skips**.
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
- Dependency vulnerability check: the initial installed pip 25.0.1 produced 12
  advisory entries (including repeated aliases), all in pip. After updating pip
  to 26.3, `pip_audit --local --skip-editable` reported **zero known vulnerability
  entries** in a report with 82 distributions. The editable project was explicitly
  skipped. This is a point-in-time advisory check, not a security certification.
- Docker build: passed using a temporary mount of the managed host's approved CA
  bundle. The first unconfigured container build failed certificate validation
  against the inspection proxy; TLS verification was retained throughout.
- Container runtime: passed as UID 10001 with networking disabled and Linux
  capabilities dropped. Synthetic dashboard AppTest, synthetic CLI generation and
  JSON/HTML exports, and a real Streamlit server's HTTP health and HTML responses
  all passed. The initial runtime attempt exposed restrictive copied source file
  permissions; the Dockerfile now makes the selected public source readable.

The refreshed [machine-readable advisory audit](foundation/DEPENDENCY_AUDIT.json)
contains package versions and advisory findings, without credentials or local
recordings. It describes this development environment, not every future release
or optional package combination.

Generated detailed reports remain in ignored `local-results/`. The existing
release and human-data evidence under `docs/` was preserved. Build hashes are
specific to each actual artifact and should be generated after the final combined
source changes, rather than copying hashes from this earlier worktree build.
