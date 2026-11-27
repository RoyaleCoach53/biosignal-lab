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
| `foundation/platform` | PR #6, isolated install, publication protection, packaging | Integrated; independent review and requirements ledger |
| `website/platform` | PR #7, actual scientific website and visual Studio canvas | Integrated; selection/grouping follow-up |
| `engine/platform` | Unit-aware methods, bounded formats, scalp/ERP rendering | Integrated; peripheral methods follow-up |
| `live/platform` | Simulator, adapters, worker lifecycle, UDP/WebSocket | Integrated; paced display/parser follow-up |
| `ai/platform` | Grouped/nested classical and spatial evaluation, CPU neural baseline | Integrated; final evidence and review |
| `studio/platform` | Executable typed DAG, visual editor, actual Live/AI nodes | Integrated; additional scientific nodes |

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

## Recovery after interrupted execution

All six worktrees and uncommitted files survived the usage interruption. The
integration branch at recovery is `1e15458`; its completed foundation, website,
initial Live and initial AI work has not yet been pushed. Native Git remote
inspection confirms none of the new development branch names exists remotely.

- Foundation integrated through `3c41950`; PR #6 and PR #7 source history retained.
- Engine through `43c1a2e` fixes NPZ float64 conversion budgets, malformed declared
  shapes and MAT preflight. Reference provenance/spectral overflow follow-up is
  committed separately before integration.
- AI through `1a24bec` adds training-only CSP, log-Euclidean covariance baselines,
  secure dataset redirects and a real synthetic CLI. Dashboard extension is being
  finished before integration.
- Studio cache framing, spectrum validation and bounded CSV preflight are on disk;
  tests and initial commit remain outstanding.
- Live optional adapters and Studio frontend files remain preserved in their
  worktrees; their final verification and commits remain outstanding.
- Parent changes include engine UI, unified navigation/CLI routing, optional extras
  and platform documentation. These are preserved as a recovery commit before
  combined verification.

The latest executed integration suite before interruption passed **173 tests**.
This does not cover unmerged subsystem extensions. The saved environment draft
includes `api.github.com`, but the running instance reports no custom allowed
hosts; the resumed API request still returns HTTP 403. Remote reviews and CI are
unverified. Review/apply the saved network rule in environment settings before
retrying that operation. Git read remains usable; push has not yet been tested.

Next action: finish reviewed subsystem commits, merge into this integration
branch, verify the unified application and isolated package, update actual results,
then push the development branches without modifying main or public releases.

## Resumed integration outcomes

The integration and six existing subsystem branches were successfully pushed to
GitHub using platform-provided native Git authentication. Main and releases were
not changed. PR #6 and PR #7 are verified ancestors of the integration branch.
Remote PR reviews and hosted CI remain unverified because the API rule is not
active on this instance. No access token was requested or extracted.

Integrated source checkpoints include engine `cf12d42`/`bdf5501`, optional Live
adapters `051c599` and worker/transports `7215a9d`, Studio `668b690`/`ddf9fbd`/
`301e22a`, frontend through `571e35e`, and AI through `e4838e7`.

- First resumed combined regression: **241 passed**, before later Studio/native
  and neural extensions were merged. A new final combined run is still required.
- Unified navigation and CLI workflow preservation: **2 passed**. Navigation
  initially exposed a component-registration defect; declaration now lives in a
  normal importable module and the regression passes.
- Actual visual editor-to-Python browser tests: **3 passed**; component tests:
  **16 passed** across desktop and emulated mobile. Earlier website 18 browser /
  33 scenario checks are historical evidence for their recorded source stage.
- Educational notebook: **4 code cells executed successfully** with unit/PSD,
  filter provenance, actual DAG execution and subject-disjoint synthetic learning.
- Independent review verified engine dtype budgets/MAT preflight/reference
  provenance, Studio nested hash framing/finite spectra/CSV preflight, and AI
  dataset hash boundaries/strict model schema. New failure regressions pass.

The integration is now labeled `0.4.0.dev0`; this is an unreleased development
version, not a declaration that v0.4 or any later acceptance gate is complete.
The package includes the offline Studio frontend; optional neural, acquisition,
interchange and notebook dependencies have separate extras. Docker now targets
the unified application and needs its final build/runtime verification.

Exact next actions: integrate the remaining reviewed follow-ups, refresh the
combined regression/numerical/security/browser/package evidence, verify the new
Docker entrypoint and safe wheel install, save final environment instructions,
update the full requirements ledger, and push the resulting development commits.
