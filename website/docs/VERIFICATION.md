# Website verification

Executed on 27 November 2026 on the Linux x86-64 cloud development host. These
results cover the PR #7 website plus the local installation controls on
`website/platform`; they do not establish physical mobile-device performance,
Safari/Firefox compatibility, clinical accuracy, or independent usability review.

## Commands and observed results

From the repository root, with Python 3.12.14 and `PYTHONPATH=src`:

```sh
python website/scripts/scenarios.py
python -m pytest website/test/test_scenarios.py -ra
```

All 33 scientific payload tests passed. The tests compare the generated traces,
spectra, band metrics, spectrograms, and Welch teaching stages against the actual
Python engine. NumPy 2.5.5, SciPy 1.18.1 and pandas 2.3.3 match
`requirements-demo.txt`. This comparison shares numerical dependencies and is
not independent physiological validation. The SDK command displayed by the
installation section was also executed and produced an analysis summary.

From `website`, using Node 24.22.3 and npm 11.19.1:

```sh
npm ci
npm run build
SITE_CHROME_EXECUTABLE=/usr/bin/chromium npm test -- --workers=2
npm audit --json
```

The production build passed. All 18 browser checks passed using Chromium
156.0.8078.79: nine desktop and nine Pixel 7 viewport/device-emulation checks.
They exercise keyboard navigation, Arabic directionality, reduced motion,
chapter restoration, actual waveform and spectrogram controls, request retry,
WebGL fallback, installation variants, clipboard success and permission failure.
The loaded-page axe checks reported no WCAG A/AA violations in either viewport.
Automated axe results do not replace manual screen-reader evaluation.
The npm registry audit reported zero known advisories on the locked dependency
tree at execution time; that is not a guarantee of vulnerability absence.

The managed network denied the Playwright browser download from
`cdn.playwright.dev`; the existing system Chromium was used through the documented
executable override. Playwright's own pinned browser, Firefox, WebKit, Windows,
and macOS were not exercised in this run.

## Performance measurement

Lighthouse 13.6.0 ran against the local production preview in mobile emulation:

```sh
CHROME_PATH=/usr/bin/chromium npx lighthouse http://127.0.0.1:4173/ \
  --chrome-flags='--headless --no-sandbox --disable-dev-shm-usage' \
  --output=json --output-path=/tmp/biosignal-website-lighthouse-mobile.json --quiet
```

The final measurement returned performance 93, accessibility 100, best practices
100, and SEO 100. First contentful paint was 1.5 seconds, largest contentful paint
2.9 seconds, total blocking time 170 ms, cumulative layout shift 0, and speed
index 1.5 seconds. An earlier run returned performance 96, first contentful paint
0.8 seconds and blocking time 30 ms; concurrent development activity and laboratory
variance prevent attributing this difference to the image preload. The final
report is `/tmp/biosignal-website-lighthouse-final-mobile.json`.
Lighthouse's experimental
agentic-browsing category scored 50 because no llms.txt or ARD manifest is supplied;
these are not platform features. This is one synthetic local measurement under
concurrent cloud work, not a production mobile benchmark or service guarantee.

The build warns about the deferred Three.js chunk exceeding 500 kB and React
client directives in the animation dependency. Both WebGL views load on demand;
the static poster works without them. No build warning was hidden or converted
into a claim of universal browser support.

Screenshots were captured outside the checkout under
`/workspace/biosignal-website-verification/`: `desktop-home.png`,
`desktop-install.png`, and `mobile-workbench.png`. They show synthetic data only.
No screenshot or previous report from the project was overwritten.

## Remaining acceptance work

Real mobile hardware, Firefox/WebKit, manual assistive-technology checks,
independent user evaluation, and production-host measurements remain unrun.
The public site deliberately uses a finite, disclosed synthetic catalogue. It
does not host human recordings, upload endpoints, arbitrary Python execution,
new AI training services, or physical acquisition controls.

## Integrated Studio verification

The integrated application now includes a separate offline visual Studio
component and Python execution service. Final checks on the integration checkout
passed the production website build, all 33 scientific scenario checks, all 18
website desktop/mobile browser checks, all 22 Studio component browser checks,
and all four actual Studio browser-to-Python checks.

The final backend run used source HEAD
`3f72d11862b54a29306a628134d14695d6bd4a81` before and after execution; dependency
and container configuration updates were still being prepared separately. This
binds the evidence to that application source, not to untested later commits.

```sh
# Repository root, using the installed Python environment:
PYTHONPATH=src python website/scripts/scenarios.py
PYTHONPATH=src python -m pytest website/test/test_scenarios.py -ra
python -m streamlit run studio_app.py --server.headless true --server.port 8503

# website directory, with the actual local Studio service running:
npm run build
SITE_CHROME_EXECUTABLE=/usr/bin/chromium npm test -- --workers=2
SITE_CHROME_EXECUTABLE=/usr/bin/chromium npm run test:studio -- --workers=2
SITE_STUDIO_URL=http://127.0.0.1:8503 SITE_CHROME_EXECUTABLE=/usr/bin/chromium npm run test:studio-backend
```

The component tests exercise actual iframe messages and exported graph JSON,
including typed connections, cycle rejection, graph parameter edits, safe
imports, keyboard/pointer movement, multi-selection, copy/paste with fresh IDs
and internal connections, grouping, group movement, undo/redo, and safe rendering
of server errors. Visual groups and positions travel separately from strict
scientific workflow JSON. Rapid edits wait for server revision acknowledgements
before further graph updates are sent.

The actual backend tests confirmed that visual edits reached Python and produced
a three-channel 500 Hz, 12-second signal through the six-node pipeline; missing
input connections disabled execution until repaired; rapid edits survived
reruns; and copying a six-node visual group executed 12 real processing nodes.
Downloaded manifests contained workflow/source hashes, dependencies, and actual
node timings. These tests do not substitute for external hardware or research
validation.

An initial concurrent verification attempt failed during browser cleanup because
the runners shared an artifact directory. Each configuration now uses a separate
`test-results` subdirectory. The final isolated reruns passed; no application
assertions were disabled. Final logs were retained outside the checkout as
`/tmp/biosignal-final-scenarios.log`, `/tmp/biosignal-final-website-build.log`,
`/tmp/biosignal-final-site-tests-isolated.log`,
`/tmp/biosignal-final-component-tests-isolated.log`, and
`/tmp/biosignal-final-backend-tests.log`.
