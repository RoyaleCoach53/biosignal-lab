# ASR implementation review and reproducible blocker

Artifact Subspace Reconstruction is not an available BioSignal Lab engine method.
The reviewed ASRpy 0.0.8 release fails calibration in the prepared environment,
before reconstruction or corruption tests can execute. No ASR efficacy, signal
preservation, real-time suitability or physiological accuracy has been established.

## Authoritative package and API review

The PyPI package identifies [DiGyt/asrpy](https://github.com/DiGyt/asrpy) as its
upstream and carries a BSD-3-Clause license. Its distributed README explicitly
states that the toolbox is not actively maintained. The wheel downloaded over
verified HTTPS was checked against PyPI's published SHA-256 digest:

```text
asrpy-0.0.8-py3-none-any.whl
f0acf5f0c00513cfba60c38d5823424bcad3035f3ddee0c1272b638d4ed20384
```

The documented API is `ASR(sfreq=..., cutoff=...).fit(mne_raw)` followed by
`.transform(mne_raw)`. Its current implementation accepts a `method` parameter
but assigns `self.method = "euclid"` internally; a Riemannian implementation must
not be presented as available. `fit()` also selects retained calibration windows
automatically. A future integration must preserve that mask and require explicit,
reviewed calibration provenance; it must not silently label incoming data clean.
The source documents calibration requirements including a high-pass-preprocessed,
sufficiently long, reasonably clean recording. A mathematical diagnostic fixture
is not evidence that those physiological calibration conditions are met.

## Executed compatibility result

The optional [diagnostic script](../../tools/diagnose_asr.py) generated a
60-second, four-channel deterministic mathematical fixture (250 Hz, seed 42),
requested Euclidean ASR with cutoff 20, and called the public API. Installed
versions were ASRpy 0.0.8, NumPy 2.5.5, SciPy 1.18.1 and MNE 1.13.2.

Calibration failed with `TypeError: only 0-dimensional arrays can be converted
to Python scalars` in `asrpy/asr_utils.py`, `fit_eeg_distribution()`, at:

```python
rows = np.arange(0, int(np.round(n * max_width)))
```

Here `max_width` comes from `np.diff()` and is a one-element array. Converting
that non-scalar array to `int` is rejected in this NumPy version. The
[machine-readable report](asrpy-compatibility-0.0.8.json) includes the fixture
hash, installed implementation source hash, exact versions and sanitized failure
frames. The diagnostic exits 1 for incompatibility, 2 when the optional dependency
is unavailable, and 0 only for completed synthetic shape/finite-value compatibility.
A 0 outcome would still not establish physiological validity or release readiness.

To reproduce in a separate disposable diagnostic environment with these versions:

```sh
python -m pip install asrpy==0.0.8 numpy==2.5.5 scipy==1.18.1 mne==1.13.2
python tools/diagnose_asr.py --output local-results/asrpy-new-diagnostic.json
```

The output path must be new. The failing package was removed from the normal
development environment after the investigation; it is not a declared project
extra or runtime prerequisite. No upstream source was modified, no compatibility
monkeypatch was applied, and no trust/checksum verification was bypassed.

## Next acceptance gate

Reassess a maintained implementation or reviewed upstream fix against the current
dependency versions. Only then implement an optional adapter with explicit
reviewed calibration, reference/channel/sampling compatibility checks, calibration
and target hashes, retained masks, cutoff/method/version provenance, resource
bounds and synthetic corruption/preservation controls. Independent physiological
efficacy and real acquisition checks remain separate, incomplete requirements.
