# Integrated verification at 8f46265

The frozen implementation `8f462659b8e47bd37156c3c42a068cafd2e40627` was
verified before further development. These results apply to that exact source,
not automatically to later feature commits or a v1.0 release.

| Check | Observed outcome |
| --- | --- |
| Combined Python regression | 358 passed; zero failed, errored or skipped; 20 documented sklearn warnings |
| Numerical engineering checks | Legacy 12/12 and extended engine 5/5 passed |
| Browser verification | 18 website, 22 component and 4 actual Studio-to-Python tests passed |
| Website scenarios/build | 33 scientific scenario tests and production build passed |
| Notebook | Four code cells executed with no error output |
| Isolated installation | Fresh wheel and sdist installed separately, outside checkout, with real CLI/engine/Live/AI/Studio/project checks |
| Distribution integrity | Archive checks, wheel RECORD, SHA-256 manifest and 58-component installed-closure inventory passed |
| Container | UID 10001, network disabled, all capabilities dropped; six pages, actual AI/Live/Studio/project behavior and HTTP checks passed |
| Security | Zero advisory entries for 122 assessed distributions; two explicit skips and a separate upstream torch query; source publication scan passed |

Machine-readable results, distribution hashes and SBOM are preserved in
[the frozen summary](verification/frozen-8f46265/summary.json),
[package report](verification/frozen-8f46265/isolated-packaging.json),
[container report](verification/frozen-8f46265/docker.json), and
[SHA256SUMS](verification/frozen-8f46265/SHA256SUMS).
The built wheel/sdist remain in
`/workspace/biosignal-verification/final-8f46265-packaging/dist` on this machine.
They were not published. Later documentation commits do not silently replace
those artifacts or their recorded hashes.

Isolated artifacts/container included `all,formats`; optional neural training,
physical acquisition and NeuroKit peripheral extras were not claimed there.
Those installed development capabilities were exercised in the combined suite.
Browser checks use Chromium and emulated mobile layouts. A separate exploratory
stale-result browser harness failed its initial readiness assumption before
exercising the behavior; its failure is preserved and is not counted as a pass.
The corresponding Python stale-result regressions passed.

These checks do not establish Windows/macOS results for this integrated source,
physical device calibration, new human datasets, clinical accuracy, independent
scientific review, legal certification or complete v1.0 acceptance.
