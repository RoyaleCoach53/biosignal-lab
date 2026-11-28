# Development checkpoint

Current verified implementation: `8f462659b8e47bd37156c3c42a068cafd2e40627`
(`0.4.0.dev0`, unreleased). Native Git confirmed that exact integration head
was pushed after the latest recovery. Main, release tags, MIT license and prior
scientific reports are preserved. This is not v1.0 acceptance.

## Completed integrated verification

The full reports survived the interruption and were inspected before retrying
anything. Both packaging and Docker helpers finished with `passed: true` and
zero command exit codes at the frozen clean source above.

- Combined regression: **358 passed, zero failed/errors/skips**, 20 documented
  sklearn warnings from intentionally single-class held-out regression folds.
- Numerical checks: **12/12 legacy + 5/5 extended engine passed**.
- Browser checks: **18 website + 22 editor component + 4 actual browser-to-Python
  tests passed**; **33** scientific website scenarios and production build passed.
- Additional stale-results browser regression: **1 passed** after correcting a
  harness readiness assumption. The initial harness failure was preserved; no
  application fix was needed. This is separate from the four core backend tests.
- Notebook: four code cells executed with no error output.
- Wheel and source distribution: separately installed into new outside-checkout
  virtual environments; real CLI, engine, Live simulation, grouped AI, Studio,
  project recovery and packaged frontend assets verified. Extras: `all,formats`.
- Docker: image `sha256:bae2546769f0e9b7536d18870fbf27c28d53eb4f49788e28df025dd3b00daee4`,
  UID 10001, network none, all capabilities dropped. Six pages, actual AI/Live/
  Studio/project behavior and HTTP health/HTML passed.
- Distribution SHA-256 and 58-component installed dependency inventory verified.
- Security: zero advisory entries for 122 assessed distributions. Editable source
  and CPU-tagged torch were explicitly skipped; a separate upstream torch 2.15.0
  query returned zero entries. This is not a native binary/security certification.

Reports and exact scope: [integrated verification](platform/VERIFICATION.md),
[frozen summary](platform/verification/frozen-8f46265/summary.json),
[security review](platform/SECURITY_REVIEW.md). Original logs and built artifacts
remain outside the checkout under `/workspace/biosignal-verification`; they were
not published. Later documentation changes do not replace those artifact hashes.

## Integrated capabilities and recovery

Recovered all six worktrees and reviewed subsystem commits. The integration
retains both PR #6 (`e740502`) and PR #7 (`ef1760f`) source ancestry and the
original 107-test EEG/EMG behavior. Additive APIs provide unit-aware processing,
validated interchange, peripheral methods, actual scalp/ERP plots, bounded Live
adapters and exact sample-clock events, grouped/spatial learning, CPU Conv1D and
EEGNet with safe JSON, 41 executable scientific nodes, reviewed optional parallel
execution, a real visual editor with groups/copy-paste, and versioned projects.

A dependency conflict was remediated through supported packages: NeuroKit2
0.2.12 permits patched setuptools 84.2.1; the build minimum is 84.1. Its five
peripheral regressions and `pip check` passed. ASRpy 0.0.8 was investigated with
verified upstream hashes and fails with the current NumPy; no fake ASR wrapper
or vendor patch was introduced. See `docs/engine/ASR_REVIEW.md`.

## Remote state and limits

Native Git read/push works with platform authentication; no token was requested
or extracted. Public GitHub pages independently verify PR #6's 8/8 and PR #7's
7/7 successful checks at their original heads; both are open with no reviews.
Those results do not validate the new integration source. No integration PR or
remote workflow run was observed. GitHub API requests remain blocked by the
runtime allowlist although `api.github.com` is saved in the environment draft.
Detailed URLs and access limits: `docs/platform/REMOTE_REVIEW.json`.

## Active next implementation work

The full original scope remains in [the requirements ledger](REQUIREMENTS_STATUS.md)
and [acceptance gates](PLATFORM_ACCEPTANCE.md). The user explicitly requested
continued engineering after the verified snapshot; these next workstreams must
not inherit its test/artifact claims:

| Workstream | Checkout / branch | Exact next action |
| --- | --- | --- |
| Model deployment | `biosignal-worktrees/ai`, `ai/platform` | Fixed-model ONNX CPU export/inference, bounded schemas and real torch/ORT comparisons |
| Real EEG/EMG workflows | `biosignal-worktrees/engine`, `engine/platform` | Official license/checksum enrollment, WFDB metadata-preserving runner and opt-in external cache; network access remains a prerequisite for real runs |
| Durable Studio | `biosignal-worktrees/studio`, `studio/durable-checkpoints` | Data-only bounded checkpoints with source/input binding and actual restart/corruption tests |
| Application handoff | `biosignal-worktrees/website`, `website/platform` | Save/open actual versioned Studio projects with separate validated view state; import never executes |
| Live robustness | `biosignal-worktrees/live`, `live/platform` | Complex/overflow clock/filter rejection and independent property-based buffer tests |
| Reproducibility tools | `biosignal-worktrees/foundation`, `foundation/platform` | Preserve portable final-verification helpers and review the new serialization/deployment paths |

Commit focused passing work, review/merge it, run affected integration checks,
refresh the combined evidence when source changes, and push dedicated branches
frequently. Keep the already verified `8f46265` artifacts immutable. Do not repeat
its expensive install/build steps merely because the session restarted.

## Remaining release gates

Software work remains: broader justified model families and deployment targets,
real task protocols, expanded dataset cohorts, plugin/workflow recovery breadth,
additional scientific reference/format cases, and comprehensive UI/documentation/
platform testing. External gates additionally include physical hardware,
independent scientific/security review, real consenting users, dataset rights/
access, account-side publication protections and maintainer approval. None can
be inferred from synthetic checks. No stable release or clinical claim is made.
