# AI development checkpoint

Worktree: `/workspace/biosignal-worktrees/ai`, branch `ai/platform`.
Parent integration must merge tested commits; this branch does not merge main,
publish releases, or claim v0.7/v1.0 completion.

Implemented and tested as of source commit `1754afc` (earlier evidence also retains
its original source commit `e4838e7`):

- Seven classical feature baselines with complete subject-disjoint outer folds,
  training-only scaling and optional nested grouped parameter selection.
- Binary training-only CSP/LDA and log-Euclidean regularized SPD covariance
  nearest-class-mean classification; analytical and leakage boundary tests.
- Explicit epoch features, safe linear JSON models, declared-license manifests,
  checksum caching, pre-follow HTTPS redirect checks, no-overwrite outputs.
- Real Streamlit feature/spatial experiments and standalone synthetic AI CLI.
- Temporal Conv1D and compact EEGNet CPU baselines with training/validation/test subject sets,
  deterministic training-only normalization, early stopping, scheduler, restored
  best validation checkpoint and fixed-architecture numeric JSON weights.
- Actual neural UI training/loss/checkpoint/held-out metrics and model export.
- EEGNet uses explicit kernels/pooling/dropout and spatial/dense max-norm
  constraints. Validation and final test forward passes respect the configured
  batch bound; the regression records every forward batch, not just training.
- Safe checkpoint schema 2 records the fixed EEGNet epoch length and validates
  integer BatchNorm counters and nonnegative variances. Schema 1 Conv1D remains
  loadable; no executable serialization is accepted.
- Reviewer-found fingerprint role/shape collision and loader coercion bugs fixed;
  complex amplitudes explicitly rejected. Tuned spatial metadata distinguishes
  base settings from actual executed fold parameters.

Latest executed AI checks: **48 passed**, 20 sklearn warnings in the deliberately
single-class held-out fold fingerprint regression cohort. These warnings are not
skips or failed assertions. Critical lint and dependency consistency passed.
Commands from this worktree:

```sh
PYTHONPATH=$PWD/src /workspace/.venvs/biosignal-lab/bin/python -m pytest -ra tests/test_ai_lab.py tests/test_ai_covariance.py tests/test_ai_neural.py
PYTHONPATH=$PWD/src /workspace/.venvs/biosignal-lab/bin/python -m ruff check --select E9,F63,F7,F82 src/biosignal_lab/ai tests/test_ai_lab.py tests/test_ai_covariance.py tests/test_ai_neural.py ai_app.py benchmarks/ai_baseline.py benchmarks/ai_neural.py
```

Optional dependencies were installed outside the checkout: scikit-learn 1.9.1
and torch 2.15.0+cpu from the official PyTorch CPU index with TLS verification.
The parent owns package extras and integration startup instructions. Torch remains
optional; its tests skip explicitly if torch is unavailable.

Fresh source-revision-bound reports preserve earlier reports:

- [Feature baseline, fingerprint v2](SYNTHETIC_BASELINE_INPUT_V2.json): 128 simulated
  epochs/eight subjects, LOSO LDA accuracy 1.0, shuffled-label control 0.5546875.
- [Temporal baseline](SYNTHETIC_TEMPORAL_BASELINE.json): train six simulated
  subjects, validate one, test one (16 epochs); held-out accuracy 1.0. Warm CPU
  inference median 0.250669 ms; p95 0.3230554 ms on the recorded CPU. Python-traced
  peak memory is not process RSS or total native allocations.
- [EEGNet baseline](SYNTHETIC_EEGNET_BASELINE.json), source `1754afc`: train six
  simulated subjects, validate one, test one (16 epochs), 25 actual training
  epochs; selected checkpoint at epoch 25. Held-out accuracy 1.0, 1,650 model
  parameters, JSON checkpoint 39,861 bytes. Warm CPU inference median 0.519777 ms,
  p95 0.59929655 ms. Python-traced peak 108,443,844 bytes excludes untraced native
  allocations and is not RSS. CPU fit and test took 8.196637176 seconds.

These demonstrations deliberately use separable synthetic inputs. No score
establishes physiological task accuracy or scientific/clinical validity.

Next action: parent integrates `1754afc` and this evidence/checkpoint commit into
the development integration branch, then completes combined verification. No
additional architecture or deployment scope is being opened before those final
checks. The optional ONNX/ONNX Runtime packages were installed during exploration
but are unused and unverified; they are not part of these implementation claims
or required extras. Do not report ONNX deployment as complete.

Remaining gates: real licensed task cohorts and evaluation, broader deep models,
cross-cohort robustness, independent scientific review, training resume state,
GPU/ONNX/TFLite/quantized/edge validation, population-level inference, and model
provenance signatures. No pretrained weights or external human data are bundled.
