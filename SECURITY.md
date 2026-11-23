# Security policy

## Supported versions

The current release line is 0.3.x, Research Alpha software. Report security defects
against the latest tagged release or `main`. No clinical or safety-critical use
is supported, and no response-time or long-term support guarantee is established.

## Reporting a vulnerability

Private vulnerability reporting is enabled for this repository. Use:

https://github.com/RoyaleCoach53/biosignal-lab/security/advisories/new

If that interface is unavailable, use a private contact method published by the
repository owner. No security email address or response-time guarantee has been
established. Do not disclose exploits, credentials, or private recordings in a
public issue. General non-sensitive questions may be raised publicly.

Provide the affected commit or version, the expected behavior, a minimal
reproduction using synthetic data, and the potential impact. Coordinate any
public disclosure with maintainers where feasible.

## Handling data and dependencies

- Use synthetic recordings for bug reports and examples whenever possible.
- Do not commit patient identifiers, raw private recordings, `.env` files, tokens,
  passwords, or credential exports.
- Treat imported files and metadata as untrusted input.
- Review parsers, export paths, resource limits, and dependency advisories before release.
- Do not run an unverified application against sensitive data.

Incorrect scientific measurements may be reported as correctness defects. If
the defect also exposes data or permits code execution, use private reporting.

Source review, credential/recording-pattern scans, and an installed-environment
advisory audit were performed for v0.3.0; see `docs/DEPENDENCIES.md` and the scientific
audit for scope. These checks are not a penetration test or a guarantee that
unknown vulnerabilities are absent. Reports include source and channel labels;
CSV exports should be treated as untrusted data when opened in spreadsheet software.
