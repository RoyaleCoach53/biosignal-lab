# Local Studio graph component

This directory contains the offline frontend for the Streamlit Studio editor.
There is no npm build step, CDN dependency, telemetry, file upload endpoint,
algorithm implementation, or arbitrary-code evaluator here. Python's Studio
registry supplies the available algorithms and validates and executes workflows.
Graph imports and parameter edits are JSON data only; editing does not execute a
workflow. Treat plugins as trusted code only after explicit review in Python.

The component uses Streamlit's version 1 iframe protocol. It accepts parent
`streamlit:render` messages with `args.workflow`, `args.catalog`, optional
`args.positions`, `args.groups`, `args.graph_digest`, `args.errors`, and `args.disabled`. It sends
`streamlit:setComponentValue` JSON objects containing `event_id`, `graph_digest`,
`workflow`, `positions`, and `groups`. The parent returns `args.event_ack` with the consumed
event ID; rapid local edits are buffered until the acknowledged revision is
available. Incoming messages must originate from the parent
window. Node names, descriptions, and errors are inserted through textContent.
The component does not accept messages from unrelated windows.

Workflows have schema version 1, a name, and 1–128 uniquely identified nodes.
Inputs map port names to `{node, port}` references. The catalogue maps node kinds
to input/output port descriptors (`kind`, `unit`, `sfreq`, `modality`) and a plain
description. Missing connections can persist as drafts; Python must prevent
execution while required inputs or scientific constraints remain invalid.
Imports support the repository's omitted defaults for parameters, inputs, source
ports, schema version, and name. Duplicate JSON keys and nonfinite numeric
overflow are rejected before parsing can silently discard or coerce their data.

Editing supports draggable titles, keyboard movement/deletion, registry search,
node creation/deletion, typed port connections, link deletion, JSON parameter
configuration, dependency layout, zoom/pan, a minimap, workflow import/export,
multi-node selection, internal copy/paste, visual grouping/ungrouping, group
movement, and 50 steps of undo/redo. Shift-click or Control/Command-click selects
multiple nodes. Control/Command+A selects all, C copies, V pastes, G groups, and
Shift+G ungroups. Copy/paste uses an internal editor clipboard, generates fresh
node IDs, and preserves only connections between selected nodes; copied consumers
with external dependencies must be reconnected before execution. Groups are
visual metadata carried outside strict scientific Workflow JSON. Each group has
an ID, text name and member IDs; scientific graph execution remains unchanged.
The Python application validates and retains view state separately. Undo history
survives acknowledged updates of the same
workflow and resets when an external workflow is loaded. JSON exports contain
the workflow definition, not signal data, group labels or results. Positions travel separately
to the Python application. Metadata checks on the client improve feedback; the
server remains authoritative because metadata may be known only at runtime.

From the repository's `website` directory, verify the browser protocol and graph
interactions with `npm run test:studio -- --workers=2`. When a system browser is
required, prefix with `SITE_CHROME_EXECUTABLE=/usr/bin/chromium`. The test harness
uses a loopback-only disposable HTTP server and real iframe protocol messages;
it does not simulate scientific results. The latest component run passed all 22 checks
passed in Chromium desktop and Pixel 7 emulation, including axe WCAG A/AA checks.
Four additional actual browser-to-Python tests passed with
`SITE_STUDIO_URL=http://127.0.0.1:8503 npm run test:studio-backend`: visual parameter
edits produced the expected three-channel 500 Hz/12-second signal through the
six-node engine workflow; incomplete drafts disabled execution until connected,
then executed seven real nodes; rapid node additions survived server revision
acknowledgements and appeared in the Python-exported nine-node workflow.
The fourth test copied a grouped six-node workflow, executed all 12 nodes in
Python, and verified that visual groups survived application reruns while the
exported scientific workflow contained no layout/group fields.
An additional targeted browser regression passed against application source
`8f462659b8e47bd37156c3c42a068cafd2e40627`: changing a successful workflow to an
incomplete draft hid prior results and disabled execution; restoring it reran
successfully; deleting its synthetic CSV source made a subsequent run of the
same workflow fail without retaining prior results or a prior execution manifest.
This test requires `SITE_STUDIO_SOURCE_ROOT` to match the server's
`BIOSIGNAL_STUDIO_SOURCE_ROOT`; CI provides a temporary synthetic-only directory.
Without that explicit file-access configuration, the extra test is reported as
skipped, while the four source-independent backend checks can still run.
These tests start from a real local Streamlit application, download actual
execution manifests, and verify workflow/source hashes and node timings.
The unified application sidebar also opened Studio and loaded its six-node graph
in a real browser. Actual Python execution is covered separately by Studio
runtime and integration tests. Physical touch devices, Firefox/WebKit, screen-reader evaluation,
and cross-tab clipboard workflows remain
unverified or unsupported; no such capabilities are presented as implemented.
