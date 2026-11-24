# BioSignal Lab site preview

The website presents BioSignal Lab v0.3.0 Research Alpha and stages the design separately from the package release. See the [public preview](https://royalecoach53.github.io/biosignal-lab/staging/). Changes under this directory are isolated from the Python package and Streamlit application.

## Build and test

Use Python 3.12, Node 24 or later, and npm. Run these from the repo root in an isolated Python environment:

```sh
python -m pip install -r website/requirements-demo.txt -e . pytest
python website/scripts/scenarios.py
python -m pytest website/test/test_scenarios.py
cd website
npm ci
npm run build
npx playwright install chromium
npm test
npm run preview
```

The last command serves a local preview. The public preview uses the `site/staging-pages` branch as the GitHub Pages source, with the contents of `website/dist/` under `staging/`. The branch serves only the compiled site, generated illustration and synthetic scenario files. The Python application and EDF support are absent from the deployment. The static host has no upload route or Python server. All fetches are internal, with a content security policy limiting connections and prohibiting form submission. The site does not collect analytics or registration data. GitHub Pages follows its own [privacy policy](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages#data-collection).

## Design

The neural atlas uses hand-authored procedural geometry. Its filaments are an illustration with no anatomical or signal interpretation. The static projection and React Three Fiber rendering share the same geometry. The renderer lazy loads when requested, renders on demand, caps pixel ratio at 1.4 and supports arrow keys or pointer drag. The poster is available before the 3D module loads and when WebGL fails. Motion for React handles the hero sequence, scroll transform and animated signal schematic. The diagram is decorative. Reduced-motion mode suppresses its movement and the hero animations. The site offers Arabic navigation and narrative in RTL and clearly identifies the English workbench.

## Data contract and reproducibility

The demonstration serves eight finite preset combinations. EEG uses eight synthetic channels at 250 Hz. The signal condition adds or removes a Gaussian amplitude transient. High-pass settings are 0.1 or 1 Hz. EMG uses one simulated channel at 1,000 Hz, two amplitudes (1× or 2×), and low-pass settings of 450 or 120 Hz. Both modalities use seed 42, 12-second signals and the Python engine's common pipeline. The Welch windows are 4 s for EEG and 2 s for EMG, with 50% overlap. Each trace shows actual samples from the same one-second excerpt starting at 4.5 s. PSD and summary metrics use the entire signal. EEG band powers use BioSignal Lab's band definitions and are omitted for EMG.

The browser selects, displays and downloads exact catalogue numbers. It scales axes for presentation and formats values for readability. The eight regression cases require exact JSON round-trip equality against Python within a single build environment for samples, frequencies, spectra, band powers and quality metrics. There is no cross-platform bitwise claim. Axis rescaling and the log lower bound are for display. The downloadable JSON retains numeric precision, simulated provenance, filter settings and dependency versions. Candidate windows are heuristic and intended for review. This demonstration is for research and education. The separate [real-data report](../docs/real_world/REPORT.md) describes the pilot's matched reference, limits on generalization and sensitivity to padding.
