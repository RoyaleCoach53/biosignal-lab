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
