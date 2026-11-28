# Reproduce distribution and container verification

`tools/verification/final_verify.py` verifies an explicitly frozen, clean source
commit. It does not publish a package, push Git, create a release or declare
v1.0 readiness. Installation/build phases need the documented package network
access. Docker runtime checks have networking disabled and use synthetic data.

Use an external Python environment with `build` installed. The selected checkout
must contain the implemented platform and `tools/release_artifacts.py`; an older
baseline checkout cannot reproduce features introduced later. Supply the full
commit SHA that you intend to verify, and keep the checkout unchanged until the
command finishes. Each output directory must be new. Dependencies/caches and logs
remain local, and previous evidence is preserved.

From a checkout containing these helpers, with your Python environment active:

```sh
python tools/verification/final_verify.py --source /path/to/biosignal-lab \
  --python /path/to/environment/bin/python \
  --expected-commit FULL_COMMIT_SHA --mode packaging \
  --output /path/to/new-packaging-results

python tools/verification/final_verify.py --source /path/to/biosignal-lab \
  --expected-commit FULL_COMMIT_SHA --mode docker \
  --output /path/to/new-container-results
```

Use the appropriate `Scripts/python.exe` path on Windows. The package phase
creates separate virtual environments using the selected `--python` interpreter;
it does not use system-site packages or an editable install. Docker verification
requires a running Docker daemon and the repository's Linux container recipe.
The helper itself is not a Windows/macOS CI result.

On managed networks with approved HTTPS inspection, append
`--ca-bundle /path/to/approved/ca-certificates.crt` to the Docker command. This
uses the Dockerfile's temporary BuildKit secret mount for build-time pip trust.
It preserves TLS verification and does not copy the bundle into the image.
Normal hosts can omit this option. `--cache-dir /path/to/writable/cache` reuses
a dependency cache; otherwise the helper creates one inside the output directory.
No credential values belong in these commands or saved reports.

The source defaults to the checkout containing the helper. `--python` defaults
to the interpreter running it. Both are explicit overrides for reproducible use
with another prepared checkout/environment. The runtime smoke program uses the
container's working directory, so a customized Docker recipe must start in the
application directory containing `platform_app.py`.

## What the phases actually exercise

The packaging phase builds one wheel and one source distribution, verifies
archive paths and wheel RECORD integrity, then installs each independently into
a new virtual environment with the `all,formats` extras. It runs dependency
consistency and actual functional checks against imports inside that environment:

- Installed CLI entrypoint, synthetic CSV generation and real JSON/HTML analysis.
- Unit-aware filtering/resampling and known-tone spectral output.
- Deterministic acquisition blocks and typed scientific DAG execution.
- Subject-disjoint classical evaluation and safe affine-model save/load inference.
- Local project revision save/recovery and packaged Studio canvas assets.

It creates a CycloneDX inventory from the installed wheel dependency closure,
generates SHA256SUMS, then independently recomputes each archive/SBOM checksum.
These are runtime metadata and integrity checks, not independent license or
scientific validity certification.

The Docker phase builds the actual recipe and executes the runtime helper as
UID 10001, with all Linux capabilities dropped and networking disabled. It checks
all six unified navigation pages for exceptions **and displayed errors**, executes
a real finite Live capture, Studio workflow and grouped AI evaluation, creates
and recovers a project document, and starts the real unified HTTP server to check
health and HTML responses. Container processes are removed after completion.
No external recording, API key or physical device is used.

These default phases do not install or claim verification of optional PyTorch
neural inference, physical/native acquisition drivers, or the NeuroKit peripheral
extra in each isolated artifact/container. Their separately executed tests and
remaining platform/OS/hardware requirements must stay distinct.

`report.json` records the source commit, helper source hashes, command exit codes,
artifact hashes or image identity, exercised capabilities and final success/failure.
The helper refuses dirty/mismatched source before builds and checks the freeze
again before reporting success. A command failure preserves its underlying exit
code and local log. Review logs for sensitive local configuration before sharing;
these helpers do not establish a secret-free log publication policy.

## Actual completed frozen-source run and helper provenance

A completed run against source
`8f462659b8e47bd37156c3c42a068cafd2e40627` used the original external helpers before
the portable argument/refactoring changes in this commit. Both phases passed;
all underlying recorded commands exited zero. The original reports and artifacts
were left unchanged:

- `/workspace/biosignal-verification/final-8f46265-packaging/report.json`.
- `/workspace/biosignal-verification/final-8f46265-docker/report.json`.
- Wheel SHA-256: `55f37a01ea38a306bb3e0b2d25c742bfca44c43038735a5cdccdfe82a5e2302c`.
- Source archive SHA-256: `732010669904071a4aa0567f66d07f2aac90e395686ff980fd7e6b484ba05fde`.
- Docker image: `sha256:bae2546769f0e9b7536d18870fbf27c28d53eb4f49788e28df025dd3b00daee4`.
- Installed-closure SBOM: 58 components; archive and SBOM checksums verified.

SHA-256 of the preserved **executed external helper files**:

| File | SHA-256 |
| --- | --- |
| `final_verify.py` | `484dd2179739e711c2564aff7b86d3341c48354a8a8fdee3fa91c4942317bdbb` |
| `runtime_smoke.py` | `aa560bce6c7ec76ac0ea876fc729d392275ad402255ae4c3ab5df6312716cfa3` |

The portable repository versions intentionally differ: they accept source,
interpreter, approved CA and cache paths, create venvs using the selected
interpreter, record their own hashes and report failures explicitly. Three
lightweight regression tests in `tests/test_verification_helpers.py` exercise
dirty-source rejection, failed-command exit-status preservation and the
requirement for a complete functional result record. Critical Ruff and helper
compilation checks also passed. The heavy artifact/container run was **not
repeated merely to relocate/refactor these helpers**; the old run's evidence is
not relabelled as execution of a different helper revision.
