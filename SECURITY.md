# Security policy

## Supported versions

No software release is currently published. The `main` branch is in publication
preparation, and v0.2.0 is not a supported clinical or production release.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting interface, when enabled, at:

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

The source code and its dependencies have not yet been recovered or audited in
this repository. The presence of this policy is not evidence of a security audit.
