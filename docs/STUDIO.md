# BioSignal Studio

Studio executes real local scientific workflows. It adds a versioned data-only
workflow format and an inspectable Python executor without changing the verified
`Recording` and `analyze` APIs. The graphical application starts from the repository:

```sh
streamlit run studio_app.py
```

The initial template runs seeded EEG simulation, the existing analysis pipeline,
JSON and HTML report generation, raw-signal Welch PSD, and EEG band integration.
The engine template adds real digital filtering and anti-aliased resampling.
Report downloads and JSON exports contain actual execution outputs.

Two additional working templates connect the subsystems:

- `examples/workflows/live_to_report.json` acquires deterministic virtual-device
  blocks through BioSignal Live, measures CPU monitoring times, and feeds the
  actual original analysis and HTML-report nodes. It does not connect to physical
  hardware or simulate elapsed wall-clock acquisition time.
- `examples/workflows/grouped_ai.json` generates labeled synthetic oscillation
  trials, runs real leave-one-subject-out LDA evaluation, fits a portable linear
  classifier, exports safe JSON coefficients, and performs actual inference.
  Fitted predictions are identified separately from out-of-subject evaluation.
  The task distinguishes generated oscillations; its accuracy is not evidence
  of physiological classification or clinical performance.

Live nodes are registered only when the actual Live module is available. AI
nodes additionally require scikit-learn and the actual AI module. The
`epoch_features` node accepts explicit event sample/class/subject metadata and
extracts real EEG/EMG features. It rejects epochs outside the recording and
overlapping samples assigned to different subject groups. Labels and subject
identity are supplied by the researcher and are not independently verified.

## Reproduce without the interface

```sh
python -m biosignal_lab.studio.cli validate examples/workflows/eeg_quality.json
python -m biosignal_lab.studio.cli run examples/workflows/eeg_quality.json --output local-results/studio-run-001
python -m biosignal_lab.studio.cli python examples/workflows/eeg_quality.json
```

`run` reserves a new output directory before executing any node. Existing
files/directories are preserved; use a new directory for a retry. Successful
runs export an execution manifest and JSON/HTML node outputs. Raw recordings
are retained in memory and are not automatically copied into those exports.
A failed run may leave the reserved directory; it does not emit a success report.

```python
from biosignal_lab.studio import Workflow, Executor, builtin_registry

with open("examples/workflows/eeg_quality.json", encoding="utf-8") as handle:
    workflow = Workflow.from_json(handle.read())
executor = Executor(builtin_registry())
order = executor.validate(workflow)
result = executor.execute(workflow)
print(result.outputs["summary"]["out"])
print(result.manifest_json())
```

## Scientific contracts and reproducibility

Each registered node declares typed input/output ports. Validation checks node
identities, parameter schemas, connections, required inputs and cycles before
execution. Port kinds include legacy microvolt recordings, engine signals with
explicit physical units and reference, analysis results, spectra, grouped feature
datasets, validated portable linear models, JSON and HTML.
Unit, sampling-frequency and modality requirements are checked against actual
runtime data. Combining channels additionally requires identical sampling rates,
sample counts and modality and distinct channel names. PSD outputs must contain
finite nonnegative powers, increasing finite frequencies within Nyquist, explicit
units and matching channel labels. Overflowing numerical output fails its node.

Workflows are strict JSON with schema version 1. Unknown structural fields,
duplicate JSON fields, nonfinite numbers, oversized imports, invalid identifiers
and duplicate node IDs are rejected. Workflow import never executes Python.
Generated Python runners embed escaped JSON as a literal; workflow names and
parameters are not interpolated as executable expressions.

The manifest records the entire workflow configuration, workflow SHA-256,
installed Python-source SHA-256, dependency versions, node revisions,
input/output fingerprints, measured execution times, retained-output size and
cache status. No raw arrays are embedded. The manifest can contain user-chosen
source filenames, channel names and parameters; review it before sharing.

The in-memory bounded LRU cache keys pure outputs by code/definition identity,
node revision, parameters, input contents and metadata, and dependency versions.
Fingerprints use length-framed nested structures, including mapping boundaries,
array shape and dtype. Detached copies prevent downstream changes or result
inspection from corrupting cached or upstream data. File-input nodes reread
files rather than caching by path. HTML reports execute each time because they
include a generation timestamp. A retry can reuse completed pure upstream nodes;
a failing node is never cached as successful.

## File access, resources and trusted extensions

File sources are disabled until the SDK/CLI caller explicitly supplies
`source_root`. Relative and absolute paths must resolve to a regular file inside
that root; traversal and symlinks resolving outside the root fail. Source bytes
are bounded before parsing, and CSV row/column counts are streamed before
allocating the complete pandas matrix. CSV data retain the existing explicit
sampling-rate, timestamp-spacing and amplitude-unit checks.

For the graphical server only an administrator can enable file reads by setting
`BIOSIGNAL_STUDIO_SOURCE_ROOT`. The interface does not accept an arbitrary server
root from a visiting user. Synthetic templates work without local file access.

`Limits` defaults bound nodes (64), per-signal values (4,000,000), retained output
bytes (128 MB), source bytes (32 MB), and cooperative run time (60 seconds).
Simulation and resampling check their expected allocation before generating data.
These are application bounds, not an operating-system sandbox or a guarantee
that third-party native code cannot allocate temporary memory.

Cancellation uses a `threading.Event` supplied to `execute(cancel=...)`; it is
checked between nodes and after the current node. It cannot interrupt a native
function mid-call. The current graphical Run button executes synchronously;
cooperative cancellation is exposed through the SDK, not a nonfunctional UI
button. Execution is sequential. Parallel scheduling and durable resumable
execution are not yet implemented.

Custom `Definition` objects require explicit `Registry.register(..., trusted=True)`.
No installed entry points or untrusted workflow fields trigger automatic plugin
loading. Plugins are arbitrary Python code with the caller's privileges, not a
sandbox. Review code and licenses before registration. Authors must increment
node revisions when behavior or external state changes, and mark any operation
with side effects or hidden mutable state `pure=False`.

## Editor and acceptance status

The application supplies a keyboard-accessible node/connection form editor,
undo/redo, JSON import/export, generated Python, graph validation, live node
progress, intermediate inspection, and real JSON/HTML report downloads. The
optional bundled visual component supplies the richer canvas; its browser
verification is reported separately from executor verification.

This work does not establish the entire v0.8 or v1.0 acceptance gate. Third-party
plugin compatibility, external hardware, independent scientific review, real
user evaluation, distributed execution, persistent caching and all requested
research node families remain separate requirements. Missing operations are not
shown as implemented scientific nodes. Studio is research software, not a
clinical tool or medical device.
