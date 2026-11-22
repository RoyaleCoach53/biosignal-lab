# Contributing to BioSignal Lab

Thank you for helping make biosignal analysis more transparent and reproducible.
The current publication stage is documented in [release status](docs/RELEASE_STATUS.md).
The historical v0.2 implementation is not yet available in this checkout.

## Discuss a change

Open a GitHub issue describing the problem, expected behavior, and why the change
would help users. For a numerical issue, include the sampling rate, units, channel
types, duration, processing parameters, dependency versions, and a minimal input.
State the expected mathematical result and its source. Report security problems
using [SECURITY.md](SECURITY.md), not a public issue.

## Prepare a contribution

1. Fork this repository and create a branch for one focused change.
2. Explain the user-visible behavior and the scientific assumptions involved.
3. Include a regression test for a reproducible calculation or parsing defect.
4. Document parameter choices, units, and relevant limitations.
5. Open a pull request with reproduction steps and actual validation output.

The supported environment and test commands will be established after source
recovery. Do not report tests as passing unless you ran them against the stated
commit. Documentation changes do not need implementation-mirroring tests.

## Scientific and data standards

- Distinguish theoretical targets, numerical measurements, and clinical evidence.
- Use explicit units; describe any conversions and reference conventions.
- Specify tolerances before interpreting benchmark outcomes.
- Keep unavailable measurements distinct from zero-valued measurements.
- Prefer deterministic synthetic fixtures for regression tests.
- Do not upload identifiable recordings, credentials, or data without permission.
- Verify dataset redistribution rights; link to restricted data rather than copying it.
- Preserve third-party copyright and license notices.

AI-assisted contributions are welcome, but their authors remain responsible for
correctness, attribution, tests, and accurate claims. Do not describe generated
material as independently reviewed without evidence of that review.

## Review

Maintainers may request a smaller reproduction, independent reference results,
or clarification of a scientific assumption. Changes affecting interpretation
should include an example of the previous and resulting behavior. Participation
is governed by the [code of conduct](CODE_OF_CONDUCT.md).
