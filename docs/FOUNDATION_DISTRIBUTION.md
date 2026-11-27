# Foundation, distribution, and audit controls

This branch preserves v0.3 scientific reports and the PR #6 student-onboarding work,
including commit `e740502d1be013647bf4ec7e0233c1f65b795c97`. It is development work,
not a declaration that v0.4 or v1.0 acceptance gates are complete.

## Cross-platform installation

Use Python 3.10 or newer. Create a virtual environment **outside the checkout** so
repository documentation checks do not scan installed dependency documentation:

```sh
python -m venv ../biosignal-env
```

On Linux/macOS use `../biosignal-env/bin/python`; on Windows use
`..\biosignal-env\Scripts\python.exe`. Substitute that interpreter for `python`
in these commands from the repository root:

```sh
python -m pip install ".[all]"
python -m pip check
python tools/first_run_check.py --require-app --require-edf
python -m streamlit run app.py
```

For development use `python -m pip install -e ".[dev,all]"`. `engine` adds optional
PyWavelets/HDF5 libraries; `ai` adds scikit-learn. These optional dependencies do not
imply every planned scientific feature has been implemented or validated.

The existing CLI names and reports remain available. Report output now defaults
to refusing collisions, including stale optional artifact/band CSVs. Choose a new
prefix for each experiment. `--overwrite` is explicit and removes optional tables
that the replacement analysis does not generate. Symbolic-link outputs are
rejected. First-run and clean-install audit reports also refuse overwrites.

## Clean installation audit

```sh
python tools/check_installation.py --venv ../new-audit-env --output local-results/new-install-audit.json
```

Both the environment and its sibling `new-audit-env-results` directory must not
exist. The report path must also be new. Failures preserve evidence for diagnosis;
retry using fresh names. This builds a wheel, installs that wheel with dashboard
extras, strips inherited Python module paths, checks that the imported package is
inside the new virtual environment, and exercises EEG/EMG CLI exports and a
synthetic dashboard. The report includes the wheel SHA-256 and dependency list.
It tests an isolated Python environment on the existing host, not a fresh OS,
physical acquisition hardware, or an independent learner session.

## Build, verify, and inventory

```sh
python -m build --outdir local-results/new-distributions
python tools/release_artifacts.py --dist local-results/new-distributions --extra all
```

The output directory must contain the current build's wheel and source archive.
The verifier checks wheel RECORD SHA-256 hashes/sizes, CRCs, duplicate/unsafe
archive paths, and source-archive links/special files. It then emits SHA256SUMS
and `sbom.cdx.json`, preserving existing evidence. On Linux/macOS check downloaded
artifacts with `sha256sum --check SHA256SUMS` (macOS: `shasum -a 256 -c SHA256SUMS`).
Windows PowerShell offers `Get-FileHash -Algorithm SHA256`; compare each result
against the manifest before installing.

The CycloneDX 1.5 inventory traverses installed project dependencies for the
selected extras. It records distribution versions, declared SPDX expressions
when available, and license-file names. It is metadata-based, host-specific, and
not an independent legal review of bundled native libraries. Retain upstream
license notices; the project's MIT license does not relicense dependencies.
Use the existing dependency-audit procedure in [DEPENDENCIES.md](DEPENDENCIES.md)
for a separate point-in-time vulnerability assessment.

## Release workflow and approvals

The manual `Verified release artifacts` workflow builds and verifies distributions
without publication by default. Publication requires all of: an explicit
`publish_to_pypi` input, running from a `v*` tag, a protected GitHub `pypi`
environment with required reviewers, and a matching PyPI Trusted Publisher
configured for this repository/workflow/environment. The publisher uses OIDC;
no API token belongs in the repository. Configure these account-side controls
before enabling publication. This work does not create a PyPI project, configure
external account protections, create a release/tag, or publish artifacts.

Do not set v1.0 or a stable classifier until the milestone evidence warrants it.
For pre-stable development use a reviewed development version; preserve existing
release tags and reports. Document API changes, migration steps, and actual test
results before a release.

## Container use

```sh
docker build -t biosignal-lab:development .
docker run --rm -p 8501:8501 biosignal-lab:development
```

The container runs as an unprivileged user and does not require credentials.
It is an optional packaging route. The base tag and dependency constraints are
not a digest-pinned reproducible supply chain; rebuild and scan images before
use. Do not put private recordings or secrets in the build context. Use local
synthetic data for demonstrations. Container validation requires a Docker daemon;
its status is reported separately from Python packaging checks.

On managed hosts with an HTTPS inspection proxy, the container build also needs
the host's trusted CA bundle. Mount it temporarily without adding credentials or
host certificates to the image, preserving TLS verification:

```sh
docker build --secret id=build_ca,src=/etc/ssl/certs/ca-certificates.crt -t biosignal-lab:development .
```

The optional `build_ca` mount affects build-time pip only. It does not turn off
certificate validation. Use your organization's approved bundle path on other
hosts. The runtime synthetic dashboard needs no outbound network access.
