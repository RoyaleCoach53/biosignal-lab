# BioSignal Lab web atlas

The [public staging site](https://royalecoach53.github.io/biosignal-lab/staging/) is the review build for PR #7. The website draws from the released Python engine. The project's actual release history and experimental-adoption materials remain in [GitHub](https://github.com/RoyaleCoach53/biosignal-lab/releases) and in the [adoption review](https://github.com/RoyaleCoach53/biosignal-lab/pull/6).

## Build and verification

Use Python 3.12 and Node 24 or later. From the repository root, in an isolated Python environment:

```sh
python -m pip install -r website/requirements-demo.txt -e . pytest
python website/scripts/scenarios.py
python -m pytest tests website/test/test_scenarios.py
cd website
npm ci
npm run build
npx playwright install chromium
npm test
npm run preview
```

Run Playwright on a deployed build by setting `SITE_TEST_URL` to its full URL with a trailing slash. Run `node scripts/capture.mjs` for screenshots. Set `SITE_RECORD=1` to record the journey with Playwright and its FFmpeg browser dependency. The staging branch serves only built static files. No request can invoke the Python engine or upload a recording there.

When Chromium is already installed on a managed development host, use
`SITE_CHROME_EXECUTABLE=/usr/bin/chromium npm test -- --workers=2` instead of
downloading another browser. The default CI still installs Playwright's pinned
Chromium. For shared cloud development, start Vite with
`npm run dev -- --host 0.0.0.0`; do not assume development processes survive a
machine restart. Generate the ignored synthetic catalogue before starting the site.

The local installation section offers Linux/macOS and Windows PowerShell commands
for the released dashboard, CLI, and Python SDK. It installs v0.3.0 from GitHub;
it does not claim newer experimental modules are released. Copy controls report
clipboard permission failures and retain selectable commands. Commands execute on
the visitor's computer only when the visitor runs them.

See [current executed verification](docs/VERIFICATION.md) for the browser, numerical,
accessibility, security-audit, and performance results and their limits.

## Interaction and accessibility

Desktop uses native scrolling with a sticky stage. Scroll position selects each chapter, drives changes in scale and positioning, and advances acquisition steps. Chapter links and teaching controls also work with a keyboard. The hero brain is interactive on demand, and the desktop acquisition stage loads a separate 3D scalp illustration while in view. Both WebGL views render on demand. On smaller screens, all chapters and visuals appear in reading order. Reduced-motion settings suppress animated transitions and use the illustrated acquisition view. A static brain poster and scalp diagram cover environments without WebGL. The Arabic option translates narrative and navigation. Diagram controls and the scientific console use English.

All procedural neuroscience illustrations depict concepts. They are artist-built shapes, without source-localization, anatomical or measurement accuracy claims. The chapter on scalp acquisition presents electrode voltage differences and analog conditioning before digitization. The story and workbench label computed plots and exported records as synthetic.

## Synthetic outputs

The catalogue has 32 combinations and one teaching example. EEG has eight channels, two transient settings, four filter presets and sampling rates of 128, 250 and 500 Hz. EMG has one channel, two amplitude settings, two filter presets and sampling rates of 1,000 and 2,000 Hz. Changing the rate generates a new series using seed 42. It is not a resample of the same recording. The 12 s recording supplies all spectral and summary calculations. The waveform view draws exact samples from the 4.5–5.5 s excerpt.

The Welch view uses 4 s EEG or 2 s EMG Hann windows, 50% overlap, constant detrending, and density in µV²/Hz. Its teaching stages use the first actual EEG segment, the detrended and Hann-windowed segment, all five engine-derived PSD frames, and the Welch mean. Automated verification compares that mean with the mean of the individual frames at relative tolerance 1e-12 and absolute tolerance 1e-14. It checks the serialized waveforms, spectra, band powers, candidate windows and metrics against direct calls to the existing engine.

The spectrogram uses the existing `time_frequency_psd` function on each processed channel. The display crops frequencies at 60 Hz for EEG and 400 Hz for EMG, using 2 s and 1 s Hann windows respectively, each with 50% overlap. The heatmap uses a log color scale, and inspection and exports retain the underlying float values. The tests check exact serialization within the build environment. Cross-platform bitwise identity is outside the scope of that test.

The project [methods](../docs/METHODS.md), [real-data pilot](../docs/real_world/REPORT.md) and [limitations](../docs/LIMITATIONS.md) document evidence and scope. The public atlas is for research and education.

## Scientific references

- [Buzsáki, Anastassiou and Koch (2012), The origin of extracellular fields and currents](https://pmc.ncbi.nlm.nih.gov/articles/PMC4907333/)
- [SciPy Welch method](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html)
- [Farina, Merletti and Enoka (2014), The extraction of neural strategies from the surface EMG](https://pmc.ncbi.nlm.nih.gov/articles/PMC4254845/)
