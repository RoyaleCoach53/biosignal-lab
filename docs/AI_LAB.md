# BioSignal AI research baselines

The AI lab executes local classical classification and verifies subject-disjoint
evaluation. It does not contain pretrained models or establish physiological,
clinical, diagnostic, or hardware performance. The bundled experiment separates
simulated 10 Hz and 20 Hz tones; it is deliberately easy and cannot substantiate
motor imagery or other physiological task accuracy.

Install the optional extra with `python -m pip install -e ".[ai,app]"`, then run
`python -m streamlit run ai_app.py`. No account, network service, hidden telemetry,
or downloaded human dataset is needed. The original EEG/EMG dashboard and APIs
remain available.

## Actual supported workflow

```python
from biosignal_lab.ai import evaluate_grouped, train_linear, save_linear_model
from biosignal_lab.ai.demo import synthetic_feature_dataset

dataset = synthetic_feature_dataset(seed=42)
report = evaluate_grouped(dataset, model="lda", cv="loso", seed=42)
model = train_linear(dataset, model="lda", seed=42)
# Choose a new path; existing models are preserved.
save_linear_model(model, "my-new-model.json")
```

`FeatureDataset(X, y, subjects, feature_names=(), provenance={})` requires finite
samples × features, integer/string labels and integer/string subject identifiers.
Inputs are copied. It preserves strict JSON provenance in reports and the input
hash. Add units, sampling rate, dataset/license/version hashes, filtering,
reference, epoch/event definitions, and feature settings to provenance for real
experiments. Class and subject identifiers are normalized to strings. They should
be pseudonyms; reports include subject-level identifiers and metrics. Do not
publish human subject information or data without the appropriate review.

`extract_epoch_features(epochs, sfreq, modality="eeg")` consumes epochs × channels
× samples and returns `(X, feature_names)`. Features remove each channel's epoch
mean. EEG includes RMS, MAV, peak-to-peak and explicitly grid-integrated Welch
band powers, requiring at least two seconds and Nyquist ≥45 Hz. Amplitudes remain
in the supplied units and powers in their square; units are never silently
converted. EMG adds waveform length, time-integrated absolute centered amplitude,
mean and median frequency. Constant-channel frequency features and inadequate EEG
bandwidth raise errors. These descriptors are not diagnostic or fatigue labels.

Supported classifier names are `lda` (automatic shrinkage), `logistic`, `qda`
(regularization 0.1), `svm`, `random_forest`, `knn` and `gradient_boosting`.
All fitting takes place in a standardization/classifier pipeline. No scaler is
fit on the entire cohort before evaluation. Defaults are baselines, not optimized
recommendations for a physiological task. QDA and neighborhood methods may be
unsuitable for tiny or ill-conditioned training sets; errors and sklearn warnings
are not suppressed.

For epoch-level spatial learning, `EpochDataset(epochs, labels, subjects, sfreq,
unit, channels=(), reference="unspecified", provenance={})` requires explicit
sampling frequency and units. `evaluate_epochs(dataset, model="csp_lda",
n_components=2)` fits binary CSP spatial filters only on each training fold,
then scales log normalized projected variances and fits shrinkage LDA. Select
2..number-of-channels components; zero-energy epochs fail explicitly. Trace
normalization and covariance shrinkage (default 0.01 toward scaled identity) are
explicit. The generalized eigenvalue behavior is tested against analytical
diagonal covariance, including rank-deficient channels. CSP filters are mixtures
of scalp potentials and are not neural source estimates.

`evaluate_epochs(dataset, model="log_euclidean")` fits a nearest-class-mean
classifier using matrix logarithms of regularized SPD epoch covariance matrices.
Distances are Frobenius distances in the log-Euclidean domain; this is not an
affine-invariant Riemannian mean implementation. Shared orthogonal-basis rotation
invariance and held-out classification are tested. This classifier does not
produce calibrated probabilities, and neither spatial classifier is currently
exported as a portable model. Nested search keys include
`csptransformer__n_components` and `regularization`, respectively.

## Leakage boundaries and uncertainty

`evaluate_grouped` uses leave-one-subject-out (`cv="loso"`) or stratified grouped
folds (`cv="group", n_splits=5`). Every sample receives exactly one outer
out-of-fold prediction; complete subjects stay together. A fold missing a training
class raises instead of generating an apparently successful incomplete analysis.
An optional nested search uses only training-subject folds:

```python
report = evaluate_grouped(
    dataset, model="logistic", cv="group", n_splits=4, seed=42,
    param_grid={"logisticregression__C": [0.1, 1.0, 10.0]}, inner_splits=3,
)
```

Reports include fold membership, selected parameters, accuracy, balanced accuracy,
macro F1, per-class precision/recall/F1/support, confusion matrices, per-subject
metrics, dependency versions, provenance, and input hash. Probability-producing
models include binary ROC curves/AUC or multiclass macro one-vs-rest AUC. SVM's
default score is not presented as a calibrated probability. Bootstrap intervals
resample whole subject accuracies, not correlated epochs. They are descriptive
percentile intervals; small cohorts, overlapping training sets and model selection
limit inferential interpretation. Balanced accuracy is defined over classes
present in the evaluated subset; subject cohorts with missing classes need care.

The caller still must prevent label-informed feature engineering, aliases for
the same subject, overlapping recordings split across identifiers, and repeated
test-set decisions. A grouped API cannot detect these scientific design errors.
Select all settings without the independent test cohort. `train_linear` fits all
supplied data for export and is not an additional accuracy evaluation.

## Safe local inference

LDA and logistic baselines export to `biosignal-linear-json` schema version
1. The file contains affine coefficients, standardization, class order and feature
names. `load_linear_model(path)` rejects unknown schemas, duplicate JSON keys,
oversized files, nonfinite values, invalid shapes and nonpositive scales. It
never loads pickle/joblib, dynamically imports model classes, or executes supplied
code. Preserve the exact feature order when calling `predict` or `predict_proba`.
Matching predictions/probabilities against sklearn are tested for binary and
multiclass models. Files are created exclusively; no default overwrite occurs.
This narrow format does not sign models, certify their provenance or provide a
sandbox for third-party code.

## Optional temporal neural baselines

`train_temporal(EpochDataset(...))` trains a documented lightweight temporal
Conv1D network by default: two temporal convolutions (16 then 32 features), ELU
activations, average pooling and a linear class head. Set
`architecture="eegnet_v1"` for a compact EEGNet implementation with eight temporal
filters (kernel 64), depth multiplier two, 16 separable filters (kernel 16),
pooling by four/eight and dropout 0.5. Spatial and dense weights have max-norm
constraints of 1 and 0.25. Padding is explicitly asymmetric to preserve temporal
length; BatchNorm uses torch defaults. The architecture follows Lawhern et al.,
*EEGNet*, J. Neural Eng. 15 (2018) 056013,
[doi:10.1088/1741-2552/aace8c](https://doi.org/10.1088/1741-2552/aace8c).
This implementation and its synthetic tests do not reproduce that paper's task
performance. No published model's accuracy or pretrained weights are claimed.

Install a compatible official PyTorch build for the intended device. For a CPU
environment using standard PyPI for other dependencies:

```sh
python -m pip install 'torch>=2.4,<3' --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e '.[neural,app]'
```

The extra declares PyTorch/scikit-learn but cannot choose a CPU/GPU wheel index
for every platform. Python, OS and torch compatibility must be checked by the
installer. The tested implementation currently trains and infers on CPU only,
with one torch thread during fitting. No GPU, ONNX/TFLite, quantization, edge or
microcontroller support is claimed.

Training uses disjoint complete training/validation/test subjects. By default the
last sorted identifier is held out for test, the penultimate for validation, and
all remaining subjects train. At least three subjects and complete training-class
coverage are required. Explicit partitions must be nonempty, disjoint and cover
every supplied subject exactly. Normalization fits training epochs only. Adam,
validation-loss learning-rate scheduling, gradient clipping and early stopping
are recorded. The minimum validation-loss checkpoint is restored before a single
test evaluation. Changing test labels is tested to leave weights, training
history and checkpoint selection unchanged. Use a predeclared protocol rather
than choosing subject assignments after examining scores.

```python
from biosignal_lab.ai import train_temporal, save_temporal_model, load_temporal_model
from biosignal_lab.ai.demo import synthetic_epoch_dataset

dataset = synthetic_epoch_dataset(seed=42)
model, report = train_temporal(dataset, seed=42, max_epochs=25, patience=5)
save_temporal_model(model, 'my-new-temporal-model.json')
restored = load_temporal_model('my-new-temporal-model.json')
probabilities = restored.predict_proba(
    dataset.X, sfreq=dataset.sfreq, unit=dataset.unit,
    channels=dataset.channels, reference=dataset.reference,
)
```

Inference requires matching sampling frequency, unit, channel order and reference;
no unit conversion or resampling is silently applied. The temporal checkpoint is
strict bounded numeric JSON for two fixed local architectures. Shape, names,
metadata, finite values and float precision are checked. Neither `torch.load`
nor pickle nor executable import strings are accepted. Checkpoints are created
exclusively and preserve existing files. Only model weights and normalization are
exported; resuming optimizer state mid-training is not implemented. Within the
tested CPU/software environment, same-seed training histories and predictions are
identical; cross-device or cross-version bit identity is not promised.
Schema version 2 records the architecture and fixed EEGNet epoch length;
version 1 Conv1D checkpoints remain loadable. EEGNet requires 64..8192 samples
per epoch and inference must match its training epoch length exactly. Integer
BatchNorm counters and nonnegative running variances are validated explicitly.

The preprocessing/batch estimate is checked before copies and normalization;
it is not a complete process/torch allocator memory guarantee. Global torch
thread/determinism/random-generator settings are restored after fitting. Train
these models in a dedicated process when other threads also invoke torch.
The UI exposes actual training, losses, checkpoint selection, held-out metrics
and numeric model export when torch is installed. The neural benchmark measures
actual synthetic holdout inference and makes no physiological task claim:

```sh
python -m pytest -ra tests/test_ai_neural.py
python benchmarks/ai_neural.py --output local-results/neural-new-run.json
python benchmarks/ai_neural.py --architecture eegnet_v1 --output local-results/eegnet-new-run.json
python -m biosignal_lab.ai.cli neural-demo --architecture eegnet_v1 --max-epochs 25 --output local-results/eegnet-new-experiment
```

## Dataset manifest and cache

`DatasetManifest` requires a dataset name/version, license identifier, HTTPS
license URL and `DatasetRecord` entries with authoritative SHA-256, subject and
train/validation/test split. Subject overlap across predefined splits and
case-colliding/unsafe paths are rejected. The license fields record declarations;
they do not constitute legal verification or permission to use a dataset.

`fetch_record(record, cache)` is offline by default and verifies existing bytes.
New download requires `download=True, license_accepted=True`. Downloading uses
normal TLS certificate verification, a timeout, bounded bytes, staging and digest
verification before exclusive creation. Existing corrupt cache entries raise
and remain untouched. Static symlink traversal is rejected; use a cache root
owned by the user, outside the repository and inaccessible to adversarial writers.
No automatic dataset discovery or human dataset is bundled or downloaded here.

## Reproduction and acceptance status

```sh
python -m pytest -ra tests/test_ai_lab.py
python -m pytest -ra tests/test_ai_covariance.py
python benchmarks/ai_baseline.py --output local-results/ai-new-run.json
python -m biosignal_lab.ai.cli demo --output local-results/ai-new-experiment
```

Choose a new output path for every run. The benchmark measures the separable-tone
baseline, a shuffled-label negative control, single-epoch warm CPU inference,
serialized model size and Python-traced peak allocation. It records machine,
software, seeds, data and source hashes. Tracemalloc is not process RSS or total
native memory; inference excludes acquisition and feature extraction. Timing is
specific to that execution environment.

Implemented: seven feature-based classical estimators, binary CSP/LDA and
log-Euclidean covariance classification, grouped/nested evaluation, explicit
feature extraction, strict JSON linear inference, manifest/cache integrity,
temporal Conv1D and EEGNet train/validation/test baselines with strict JSON weights,
synthetic browser workflows, and analytical/security/regression tests.

Incomplete v0.7/v1.0 gates: affine-invariant Riemannian approaches, additional deep architectures
(including recurrent, attention and temporal convolutional networks), real motor imagery/P300/SSVEP/blink/EMG
task cohorts and their licenses, preprocessing fit checks beyond the caller-supplied
feature boundary, independent cohorts/review, imbalance interventions, training
optimizer-resume checkpoints, experiment database, robustness studies,
ONNX/TFLite/quantization/GPU/edge/microcontroller validation. No button, registry
entry, accuracy claim or release-completion claim is provided for those features.
