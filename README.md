# BioSignal Lab

Open-source EEG and EMG analysis for biomedical engineering education and research.

**Publication status: preparation in progress; v0.2.0 has not been released.**
The previously generated v0.2 source archive and its audit artifacts have not yet
been recovered into this repository. This checkout currently contains newly
prepared project documentation, not an installable signal-analysis application.
Historical reports of 73 passing tests have **not** been independently reproduced
from this checkout. No clinical validation is claimed.

## Purpose

BioSignal Lab aims to help students and researchers inspect biosignals, understand
signal quality, and reproduce time-domain and spectral measurements with explicit
units and processing settings. The release should make every reported result
traceable to source code, input data, parameters, and a test or benchmark.

## Installation and usage

The repository can be checked out with:

```sh
git clone https://github.com/RoyaleCoach53/biosignal-lab.git
cd biosignal-lab
```

There is currently no verified installation command, package, CLI, or application
entry point. These instructions will be completed against the recovered source
and a clean-environment installation before v0.2.0 is tagged. Do not infer a
working implementation from the project name or roadmap.

## Planned v0.2 scope — pending source verification

- EEG spectral analysis with explicitly defined frequency bands and PSD units.
- EMG root mean square (RMS) measurements with appropriate sampling and filtering.
- Timestamp, channel type, unit, and missing-data validation.
- Signal-quality flags that support human review.
- Reproducible synthetic examples and scientific regression tests.

These are release targets, not assertions about code available in this checkout.

## Documentation

| Document | Purpose |
| --- | --- |
| [Release status](docs/RELEASE_STATUS.md) | Verified state and remaining release gates |
| [Scientific methodology](docs/SCIENTIFIC_METHODOLOGY.md) | Measurement definitions and validation protocol |
| [Scientific limitations](docs/LIMITATIONS.md) | Limits on interpretation and use |
| [Benchmark protocol](benchmarks/README.md) | Reproduction and reporting requirements |
| [Examples and data](examples/README.md) | Data provenance and example requirements |
| [Roadmap](ROADMAP.md) | Development and adoption priorities |
| [Contributing](CONTRIBUTING.md) | How to report issues and contribute |
| [Security](SECURITY.md) | Responsible vulnerability reporting |
| [Code of conduct](CODE_OF_CONDUCT.md) | Community expectations |
| [Attribution](NOTICE.md) | Provenance and third-party attribution policy |

## Scientific responsibility

Numerical agreement on synthetic signals checks selected calculations under
specified conditions. It does not establish physiological validity, diagnostic
accuracy, safety, or clinical usefulness. BioSignal Lab is not a medical device
and must not be used to make diagnosis, treatment, or emergency-care decisions.

The publication process will withhold the `v0.2.0` release until the original
source is inspected, available tests are rerun, scientific checks are reproduced,
and dependencies and licensing are reviewed. No benchmark values are published
as verified results at this stage.

## Current automated checks

The `Documentation only` GitHub Actions workflow checks local Markdown file
links using Python 3.9 or later:

```sh
python tools/check_docs.py
```

This helper was newly authored for repository preparation. Its success says
nothing about application correctness or scientific validation. Implementation
CI will be added after the original source and test commands are verified.

## Contributing and adoption

Contributions should start with a reproducible problem, a small shareable dataset
with documented provenance, and an expected result. Useful early contributions
include independent numerical checks, documentation review, and review of signal
processing assumptions. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

New material in this repository is available under the [MIT License](LICENSE).
Licensing and attribution of the recovered source must be checked before it is
added. External datasets and dependencies retain their own licenses.
