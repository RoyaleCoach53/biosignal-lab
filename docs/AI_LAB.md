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

Only LDA and logistic baselines export to `biosignal-linear-json` schema version
1. The file contains affine coefficients, standardization, class order and feature
names. `load_linear_model(path)` rejects unknown schemas, duplicate JSON keys,
oversized files, nonfinite values, invalid shapes and nonpositive scales. It
never loads pickle/joblib, dynamically imports model classes, or executes supplied
code. Preserve the exact feature order when calling `predict` or `predict_proba`.
Matching predictions/probabilities against sklearn are tested for binary and
multiclass models. Files are created exclusively; no default overwrite occurs.
This narrow format does not sign models, certify their provenance or provide a
sandbox for third-party code.

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
python benchmarks/ai_baseline.py --output local-results/ai-new-run.json
```

Choose a new output path for every run. The benchmark measures the separable-tone
baseline, a shuffled-label negative control, single-epoch warm CPU inference,
serialized model size and Python-traced peak allocation. It records machine,
software, seeds, data and source hashes. Tracemalloc is not process RSS or total
native memory; inference excludes acquisition and feature extraction. Timing is
specific to that execution environment.

Implemented: seven classical estimators, grouped/nested evaluation, explicit
feature extraction, strict JSON linear inference, manifest/cache integrity,
synthetic browser workflow, and meaningful analytical/security/regression tests.

Incomplete v0.7/v1.0 gates: CSP/Riemannian end-to-end evaluation, deep architectures
(including EEGNet and temporal networks), real motor imagery/P300/SSVEP/blink/EMG
task cohorts and their licenses, preprocessing fit checks beyond the caller-supplied
feature boundary, independent cohorts/review, imbalance interventions, training
checkpoints/scheduling/early stopping, experiment database, robustness studies,
ONNX/TFLite/quantization/GPU/edge/microcontroller validation. No button, registry
entry, accuracy claim or release-completion claim is provided for those features.
