# AI development checkpoint

Worktree: `/workspace/biosignal-worktrees/ai`, branch `ai/platform`.
Parent integration must merge tested commits; this branch does not merge main,
publish releases, or claim v0.7/v1.0 completion.

Implemented and tested as of source commit `e4838e7`:

- Seven classical feature baselines with complete subject-disjoint outer folds,
  training-only scaling and optional nested grouped parameter selection.
- Binary training-only CSP/LDA and log-Euclidean regularized SPD covariance
  nearest-class-mean classification; analytical and leakage boundary tests.
- Explicit epoch features, safe linear JSON models, declared-license manifests,
  checksum caching, pre-follow HTTPS redirect checks, no-overwrite outputs.
- Real Streamlit feature/spatial experiments and standalone synthetic AI CLI.
- One temporal Conv1D CPU baseline with training/validation/test subject sets,
  deterministic training-only normalization, early stopping, scheduler, restored
  best validation checkpoint and fixed-architecture numeric JSON weights.
- Actual neural UI training/loss/checkpoint/held-out metrics and model export.
- Reviewer-found fingerprint role/shape collision and loader coercion bugs fixed;
  complex amplitudes explicitly rejected. Tuned spatial metadata distinguishes
  base settings from actual executed fold parameters.

Latest executed AI checks: **44 passed**, 20 sklearn warnings in the deliberately
single-class held-out fold fingerprint regression cohort. These warnings are not
skips or failed assertions. Critical lint passed. Commands from this worktree:

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

Both demonstrations deliberately use separable synthetic inputs. Neither score
establishes physiological task accuracy or scientific/clinical validity.

Next independent work: add a documented compact EEGNet architecture if feasible
within the existing disjoint-partition/safe-checkpoint system, then run actual
training and failure tests. Otherwise extend local feature dataset evaluation
without adding fabricated human-task claims. Parent must integrate latest branch,
run full platform regression, and retain incomplete milestones in the global
acceptance report.

Remaining gates: real licensed task cohorts and evaluation, broader deep models,
cross-cohort robustness, independent scientific review, training resume state,
GPU/ONNX/TFLite/quantized/edge validation, population-level inference, and model
provenance signatures. No pretrained weights or external human data are bundled.
