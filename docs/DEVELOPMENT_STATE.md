# Development checkpoint

This is an integration branch, not a v1.0 release or a claim of completed scientific validation.

## Baseline and recovery

- Starting commit: `bff6d67adfbba1d8ef35fdb80acc21284c5683f6` (v0.3.0 main).
- Retrieved every advertised remote branch and PR #6/#7 source refs through native HTTPS Git.
- PR #6 tip: `e740502d1be013647bf4ec7e0233c1f65b795c97`, including stale clean-install result guards.
- PR #7 tip: `ef1760feff943b455a905268b0592b03661c9f82`, cinematic website and actual synthetic workbench.
- GitHub GraphQL PR listing returned Forbidden. Remote reviews and CI conclusions have not been verified.
- Existing scientific evidence, tags, MIT license and published reports must be preserved.

## Environment verified

Python 3.12.14. External virtual environment: `/workspace/.venvs/biosignal-lab`.
Core, app, EDF and development extras installed. Writable caches reside under
`/workspace/.cache`. An in-checkout virtual environment caused the documentation
scanner to read third-party Markdown; it was replaced by the external environment.

- Original tests: **107 passed, no skips**, including dashboard AppTest and generated EDF.
- Numerical reference benchmark: **12/12 passed**.
- Dependency consistency, critical lint, compilation, documentation links: passed.
- Source distribution and wheel build: passed.
- Dashboard startup, HTTP health and HTML response: passed.

Local current-run outputs are under ignored `local-results/`. These checks do not
establish fresh operating-system reproducibility, hardware compatibility or
independent scientific review.

## Active work and ownership

Independent worktrees under `/workspace/biosignal-worktrees`:

| Branch | Scope | Status |
| --- | --- | --- |
| `foundation/platform` | Recover PR #6, install audit, publication protection, packaging | In progress |
| `website/platform` | Recover PR #7, browser/scientific validation, accessibility | In progress |
| `engine/platform` | New unit-aware processing API, analytical reference checks | In progress |
| `live/platform` | Simulation, ring buffer, streaming processing and diagnostics | In progress |
| `ai/platform` | Subject-grouped evaluation, safe models and data manifests | In progress |
| `studio/platform` | Typed executable DAG, provenance, workflow builder | In progress |

The integration branch is `integration/research-platform`. Keep legacy `Recording`
and `analyze` behavior intact. New subsystems live in separate packages. Only
functional, tested operations may appear as available in interfaces. New signal
units must not be forced into the legacy microvolt representation.

## Release gates and remaining work

No new milestone has been declared complete. Required next steps: collect and
review subsystem commits, integrate them, run combined regression/numerical/UI
and isolated distribution checks, persist actual measurements, and update this
document with exact outcomes and next actions. Push the reviewed integration
branch and create a PR if remote authorization supports those operations.

Physical devices, independent researchers, real user evaluation, external dataset
cohorts and publication approvals remain incomplete. Do not invent them, alter
protocol thresholds to pass, or mark v1.0 complete based on synthetic checks.

## Exact next action

Review each subsystem diff and test report before integration. Maintain this
checkpoint as work proceeds, preserving failures, unsupported features and
unexecuted checks alongside passing outcomes.
