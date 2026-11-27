# Studio development checkpoint

Branch: `studio/platform`; worktree: `/workspace/biosignal-worktrees/studio`.
The parent integration branch owns merging and pushing. This worktree does not
modify shared CLI routing, package declarations or the original dashboard.

Implemented: strict versioned workflow model, reviewed built-in scientific nodes,
typed DAG validation/execution, runtime unit/rate/modality contracts, finite PSD
contracts, source-bound framed fingerprints, bounded detached LRU caching,
cooperative cancellation/deadlines, explicit trusted registry, CSV root and
pre-allocation count limits, JSON/Python export, no-overwrite standalone CLI,
functional Streamlit editor/inspection/report exports, synthetic benchmark and
working example workflows.

Independent foundation review found nested mapping hash ambiguity and acceptance
of overflowed PSDs. Both were fixed and regression-tested. Definition fingerprints
now distinguish callable source/identity; plugin authors still own hidden-state
revision discipline. CSV count preflight now occurs before full pandas allocation.

Latest focused verification: **26 passed, no skips** using the Studio worktree
with the engine worktree appended to `biosignal_lab.__path__` for integration.
The engine is not copied into or modified by this workstream. The suite exercises
AppTest execution, metadata-preserving engine filters/resampling, node contracts,
malformed imports, code-generation escaping, failure retry, bounded cache,
cancellation, source traversal, CSV limits and numeric overflow. Parent must
rerun against the final merged package. Critical Ruff checks passed before the
last additional regression cases; rerun before integration.

The first synthetic timing run preceded framed fingerprints and remains in the
ignored local-results directory. The fresh framed-source report is
`SYNTHETIC_EXECUTION_FRAMED.json`. These are two synthetic runs, not performance
claims about clinical data or physical acquisition hardware. Python allocator
peaks are not process RSS.

Next exact actions:

1. Commit this implementation for parent integration and rerun full merged tests.
2. Integrate the website agent's separately owned static visual editor, verify
   iframe protocol, desktop/mobile interactions, and package-data inclusion.
3. Add real simulated acquisition and subject-grouped AI nodes using completed
   Live/AI APIs, with integration tests and actual measured output, before exposing
   them in the registry. No placeholder acquisition or model nodes exist.
4. Assess remaining editor and v0.8 acceptance requirements honestly; parallel
   scheduling, durable execution and all advanced node families remain incomplete.

## Resumed integration follow-up

Commit `668b690` contains the first runtime/application implementation. Commit
`ddf9fbd` moves component declaration into an importable module so unified
`st.Page` navigation works and adds the acknowledged single-flight event protocol.
The parent integrates the website agent's separately tested canvas files.

Implemented real Live/AI nodes: `live_simulate`, `ai_demo`, `epoch_features`,
`ai_evaluate`, `ai_train`, `ai_model_json`, and `ai_predict`. Optional modules are
checked before registration. The two new templates execute actual simulated
acquisition to original analysis/report and actual grouped evaluation to portable
training/inference. No physical-device or unimplemented deep-learning nodes are
exposed. Epoch extraction rejects cross-subject overlap in the same samples.
CSV preflight additionally rejects row-width mismatches (preventing pandas inferred
indices) and duplicate/empty headers; four independent-review regressions cover it.

Focused integration suite after these changes: **34 passed, no skips** with the
completed Engine/Live/AI worktrees added to the package import path. This is not
final merged-branch validation; the parent must repeat it after integration.
Critical Ruff checks passed. Synthetic integration artifact
`SYNTHETIC_LIVE_AI.json` records actual 4-node virtual acquisition plus analysis
(1,000 samples) and 5-node AI workflow (32 synthetic trials, 4 held-out subject
folds). Observed single-run elapsed times were about 0.219 s and 1.212 s,
respectively. Python allocator peaks were about 1.42 MB and 23.43 MB. These are
single local synthetic observations, not physiological, end-to-end hardware,
throughput-distribution or process-RSS claims.

Exact next action: parent cherry-pick the follow-up commit, run the full merged
suite plus actual unified-navigation/browser flows, and retain the external
physical hardware, scientific review and real-user gates as incomplete. Durable
execution, parallel DAG scheduling, plugin compatibility certification and all
requested advanced research node families remain unimplemented.
