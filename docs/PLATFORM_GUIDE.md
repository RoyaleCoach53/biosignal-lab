# Local development platform

The platform integration is unreleased research software. The existing v0.3
EEG/EMG workflow and historical evidence are retained. Use the
[acceptance ledger](PLATFORM_ACCEPTANCE.md) and [checkpoint](DEVELOPMENT_STATE.md)
to distinguish implemented software, executed checks and incomplete release gates.

## Install and start

Use Python 3.10 or newer (this environment was tested with 3.12). From the repository:

```sh
python -m venv ../biosignal-venv
# Linux/macOS
source ../biosignal-venv/bin/activate
# Windows PowerShell alternative:
# ..\biosignal-venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,all,formats,physiology]"
python -m pip check
python -m streamlit run platform_app.py
```

Use an environment outside the checkout to keep third-party files outside
repository documentation and publication scans. In managed cloud environments,
use the saved environment installation/start instructions. No account, key or
external service is needed for calibration, simulation or the grouped synthetic
learning demonstration. Optional real hardware or dataset access has additional
requirements; it is never automatically enabled.

The navigation includes the preserved Signal Explorer, unit-aware Scientific
Engine, finite simulated Live Lab, synthetic AI Lab, executable Studio and local
Projects. Individual pages can be started with `streamlit run app.py`,
`engine_app.py`, `live_app.py`, `ai_app.py`, `studio_app.py` or `workspace_app.py`.
Changing page ends its display; it does not establish a background acquisition
service. Interface errors must remain visible rather than replaced by fake data.

## Engine and units

The legacy `Recording` API always represents microvolts. New measurements use
`biosignal_lab.engine.Signal` with explicit units, reference and modality.
Do not put PPG arbitrary units or EDA conductance into the legacy voltage field.

```python
import numpy as np
from biosignal_lab.engine import Signal, FilterSpec, filter_signal, welch_psd

fs = 250
t = np.arange(fs * 10) / fs
signal = Signal(np.sin(2 * np.pi * 10 * t)[None], fs, ("Calibration",),
                modality="eeg", unit="uV", reference="synthetic")
filtered = filter_signal(signal, FilterSpec(cutoff=(1, 40)))
frequency, density = welch_psd(filtered)
assert abs(frequency[density[0].argmax()] - 10) < 1
print(filtered.history)
```

This verifies tone processing, not a person's physiology. Zero-phase filtering
is acausal and squares the one-pass magnitude response. Causal streaming filters
preserve state across chunks and require explicit resets after discontinuities.
See [engine methods and format support](ENGINE.md).

## Execute a saved scientific experiment

```sh
biosignal-lab workflow validate examples/workflows/eeg_quality.json
biosignal-lab workflow run examples/workflows/eeg_quality.json --output local-results/experiment-001
biosignal-lab workflow python examples/workflows/eeg_quality.json > local-results/reproduce.py
```

Use a new output directory on every run. The manifest binds the workflow digest
and execution provenance. Exported Python uses the same validated runtime; it
does not substitute an independent numerical implementation. CSV source nodes
require an explicitly allowed input directory. Plugins execute Python and must
be reviewed and registered with explicit trust. See [Studio](STUDIO.md).

## Live and AI laboratories

Live Lab shows actual simulated sample blocks, buffer/drop diagnostics and
causal processing output. Simulation advances a virtual clock; CPU processing
time is not sensor-to-display latency. Playback uses safe bounded recording
archives. See [streaming contracts and measurements](live/README.md).

AI Lab evaluates simple synthetic tasks with complete subject groups held out.
Scaling/model selection must fit within training folds. A deliberately easy
tone classification result is not an EEG task accuracy result. Safe exported
linear models contain JSON coefficients and never deserialize pickle/joblib.
See [AI Lab](AI_LAB.md) for grouping, uncertainty and dataset limitations.

## Projects and session recovery

Projects store bounded JSON documents in a directory you explicitly select.
Every save produces a new revision; earlier revisions remain recoverable after
restarting the application. Workflow JSON can be exported from Studio, saved as
a project document, then exported and imported into Studio in a later session.
This interchange is explicit; project saving does not copy recordings or
automatically restore a running device or experiment.

The SDK offers the same store:

```python
from biosignal_lab.workspace import Workspace
store = Workspace("local-results/projects")
project = store.create_project("Calibration study")
revision = store.save(project, "settings", {"seed": 42, "sfreq": 250})
assert store.load(project, "settings", revision)["seed"] == 42
```

The store is intended for one trusted local user; it is not a multi-user server
authorization boundary. File names and descriptions can contain sensitive
metadata. Review JSON and reports before sharing them.

## Website development

```sh
python website/scripts/scenarios.py
cd website
npm ci
npm run build
npm run dev -- --host 0.0.0.0
```

The payload generator runs the actual Python pipeline for a finite catalogue of
synthetic inputs. Browser controls select those computed scenarios; they do not
claim unrestricted server-side analysis. The [website guide](../website/README.md)
describes browser verification and the existing-system-Chromium fallback.

## Reproduce checks and handle failures

Run `python -m pytest -ra` and `python benchmarks/verify.py --output` with a new
report path. Build into a new directory with `python -m build --outdir PATH`,
then verify with `python tools/release_artifacts.py --dist PATH --extra all`.
Existing scientific reports are preserved, so a reused path deliberately fails.

If a module is unavailable, install its documented optional extra rather than
silently changing the analysis. If filters reject a short recording, use a
justified window/filter policy and retain the resulting transient limitations.
If a dataset checksum fails, preserve the input for diagnosis and do not weaken
the expected hash. If a subject split lacks a class, amend the cohort protocol
before evaluation rather than splitting correlated windows at random.

Hosted CI, Windows/macOS execution, physical acquisition, expanded licensed
cohorts, independent review and real user evaluation are separate gates. Their
absence must remain in the release readiness assessment.
