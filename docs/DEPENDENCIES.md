# Dependency and license review

Release refresh: 2026-11-23. The local Windows/Python 3.12 environment was created
on 2026-11-22 and reused for the final checks. Package analysis requires NumPy, SciPy, and pandas;
MNE enables EDF import, while Streamlit and Plotly enable the optional dashboard.
There is no remote model/API service or required credential.

## Direct analysis and application dependencies

| Package | Recorded version | License metadata |
| --- | --- | --- |
| NumPy | 2.5.5 | BSD-3-Clause and bundled permissive component notices |
| SciPy | 1.18.1 | BSD-style project license plus bundled-library notices |
| pandas | 2.3.3 | BSD-3-Clause |
| MNE-Python | 1.13.2 | BSD-3-Clause |
| Streamlit | 1.67.0 | Apache-2.0 |
| Plotly | 6.9.0 | MIT |

Versions and license identifiers were read from installed distribution metadata.
Dependency wheels can contain additional notices for compiled/bundled components;
their original distributions remain authoritative. This repository and release
wheel do not vendor these dependencies. The project's MIT license does not
relicense third-party packages or future external datasets.

## Known-advisory check

```sh
python -m pip install --upgrade pip pip-audit
python -m pip_audit --local --skip-editable --format json --output dependency-audit.json
```

After updating the review environment's pip from 25.0.1 to 26.3, the release check
audited **78 installed distributions and found zero known vulnerability entries**.
The editable development package was intentionally omitted with `--skip-editable`;
its source was reviewed separately, and no PyPI publication is claimed. The initial
findings concerned the environment's pip, not an application runtime dependency.

The full machine-readable record is [DEPENDENCY_AUDIT.json](DEPENDENCY_AUDIT.json).
The [pinned environment snapshot](../requirements/validation-py312-windows.txt)
includes test, packaging, and audit tools as well as application dependencies.
`pip check` also reported no broken requirements. CI resolves supported versions
separately on Python 3.10/3.12 and Windows/Linux.

This is a point-in-time advisory check, not a guarantee against unknown defects,
malicious future package versions, supply-chain compromise, or all allowed
historical dependency versions. Refresh advisories and test before upgrading.

## Source and publication checks

- Inspected recovered source, tests, dashboard, and packaging configuration.
- Scanned source and publication files for common credential/private-key patterns
  and unnecessary personal contact details; no matches were detected.
- Preserved original MIT copyright and permission notices.
- Kept human recordings, local outputs, and private configuration out of version control.
- Pinned GitHub Actions to commit revisions, limited CI token permissions to read,
  and disabled checkout credential persistence.
- Enabled private vulnerability reporting, secret scanning/push protection, and
  dependency visibility/alerts on the public repository.

These measures do not replace input-fuzzing, a penetration test, or a full
independent software-security audit. See [SECURITY.md](../SECURITY.md).
