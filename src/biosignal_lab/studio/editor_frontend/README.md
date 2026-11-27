# Local Studio graph component

This directory contains the offline frontend for the Streamlit Studio editor.
There is no npm build step, CDN dependency, telemetry, file upload endpoint,
algorithm implementation, or arbitrary-code evaluator here. Python's Studio
registry supplies the available algorithms and validates and executes workflows.
Graph imports and parameter edits are JSON data only; editing does not execute a
workflow. Treat plugins as trusted code only after explicit review in Python.

The component uses Streamlit's version 1 iframe protocol. It accepts parent
`streamlit:render` messages with `args.workflow`, `args.catalog`, optional
`args.positions`, `args.graph_digest`, `args.errors`, and `args.disabled`. It sends
`streamlit:setComponentValue` JSON objects containing `event_id`, `graph_digest`,
`workflow`, and `positions`. Incoming messages must originate from the parent
window. Node names, descriptions, and errors are inserted through textContent.
The component does not accept messages from unrelated windows.

Workflows have schema version 1, a name, and 1–128 uniquely identified nodes.
Inputs map port names to `{node, port}` references. The catalogue maps node kinds
to input/output port descriptors (`kind`, `unit`, `sfreq`, `modality`) and a plain
description. Missing connections can persist as drafts; Python must prevent
execution while required inputs or scientific constraints remain invalid.

Editing supports draggable titles, keyboard movement/deletion, registry search,
node creation/deletion, typed port connections, link deletion, JSON parameter
configuration, dependency layout, zoom/pan, a minimap, workflow import/export,
and 50 steps of undo/redo. Undo history survives acknowledged updates of the same
workflow and resets when an external workflow is loaded. JSON exports contain
the workflow definition, not signal data or results. Positions travel separately
to the Python application. Metadata checks on the client improve feedback; the
server remains authoritative because metadata may be known only at runtime.

From the repository's `website` directory, verify the browser protocol and graph
interactions with `npm run test:studio -- --workers=2`. When a system browser is
required, prefix with `SITE_CHROME_EXECUTABLE=/usr/bin/chromium`. The test harness
uses a loopback-only disposable HTTP server and real iframe protocol messages;
it does not simulate scientific results. On 27 November 2026, all 12 checks
passed in Chromium desktop and Pixel 7 emulation, including axe WCAG A/AA checks.
Actual Python execution is covered separately by Studio runtime and integration
tests. Physical touch devices, Firefox/WebKit, screen-reader evaluation,
multi-node selection, node grouping, and cross-tab clipboard workflows remain
unverified or unsupported; no such capabilities are presented as implemented.
