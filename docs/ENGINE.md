# Additive scientific engine

The `biosignal_lab.engine` API extends the v0.3 EEG/EMG toolkit without changing
`Recording`, `AnalysisConfig`, `analyze`, the existing CLI, or recorded release
evidence. These are research primitives, not diagnostic tools or a completed
v0.5 release. A result must be interpreted with its acquisition and processing
settings.

## Units and provenance

`Signal(data, sfreq, channels, modality="eeg", unit="uV", reference=None,
metadata={})` contains finite channel-by-sample data. It copies input data and
metadata, marks the owned array read-only, and stores labels, explicit units,
sampling frequency and acquisition reference. Arrays can deliberately have
write protection overridden by callers; do not share with code that mutates
internal state. Metadata is copied and protected at its top level, not recursively
frozen. Applications should treat nested metadata and history as read-only.

Supported modality labels are EEG, EMG, ECG, EOG, PPG, EDA and `other` in lowercase.
This labels the signal; it does not validate physiological identity. Electrical
units (`V`, `mV`, `uV`), conductance units (`S`, `uS`) and arbitrary units (`a.u.`)
are separate. `to_unit()` rejects conversion between incompatible quantities.
PPG is not assumed to be voltage or calibrated blood volume. Transformations
retain metadata and append operation parameters to `history`. Explicit reference
transforms update the reference description. `Signal.from_recording()` bridges
the original toolkit; it does not guess an acquisition reference.

Missing data are not silently accepted. `repair_missing()` performs bounded
interior linear interpolation and records its limits and warning messages. Gaps
at boundaries, infinities, excessive duration or missing fraction fail. Filled
values are estimates, not recovered physiology.

## Filtering and sampling

`FilterSpec` accepts Butterworth (`butter`), Chebyshev I/II (`cheby1`, `cheby2`),
Bessel (`bessel`), elliptic (`ellip`) and windowed FIR (`fir`). Types are lowpass,
highpass, bandpass, bandstop and notch. Frequencies are Hz strictly inside
Nyquist. IIR order is limited to 20; FIR `order` means odd tap count, at least 3.
The ripple and stopband attenuation settings apply to families that use them.
Notch uses SciPy's second-order IIR design with explicit quality factor.

`filter_signal(signal, spec)` records causal or forward-backward direction,
odd padding and pad length. Forward-backward filtering is acausal and squares
the single-pass magnitude response; it is not appropriate for real-time use.
Padding policy changes results at boundaries. Padding is not a guarantee of
settled response: trim and assess transients for the selected filter and data.
Causal one-shot filtering starts at zero state and includes startup transients.

`StreamingFilter(FilterSpec(phase="causal", ...), sfreq, n_channels)` persists
filter state across `.process(chunk)` calls. One consumer owns each instance;
call `.reset()` explicitly after a discontinuity. Arbitrary chunk partitioning
matches the one-shot causal reference in tests. The class does not perform
thread synchronization or infer dropped samples.

`resample_signal()` uses rational polyphase FIR resampling, a Kaiser window
(beta 5), and line extension. It rejects inaccurate rational approximations and
excessive outputs. Anti-alias filtering is tested using a tone above the new
Nyquist frequency. Edge transients remain. `detrend_signal()` supports constant
and linear detrending. `normalize_signal()` provides z-score and median/MAD
normalization, outputs arbitrary units and rejects zero dispersion.

## Spectra and time-frequency transforms

- `fft_spectrum()` returns one-sided rectangular-window amplitudes in input units,
  with correct DC/Nyquist scaling. No mean removal or window correction is hidden.
- `welch_psd()` returns Hz and input-unit-squared/Hz with Hann segments, 50% overlap,
  constant segment detrending and density scaling. Requested windows must fit.
- `spectrogram()` uses the same density convention; `stft()` returns complex
  coefficients in input units without boundary extension or tail padding.
- `multitaper_psd()` averages DPSS periodograms with explicit time-bandwidth and
  taper count. It removes channel means and uses equal taper weights. This is
  not adaptive multitaper weighting or a confidence-interval estimator.
- `integrate_band()` interpolates spectral endpoints and integrates with the
  trapezoidal rule. An incompletely observed band fails rather than becoming zero.
- `spectral_entropy()` computes Shannon entropy of normalized discrete power
  weights, optionally divided by log2(number of bins). Zero total power fails.
- `wavelet_transform()` and `discrete_wavelet()` require PyWavelets. CWT values
  are coefficients, not a calibrated PSD. Neither transform automatically removes
  boundary effects. Decomposition levels and output sizes are bounded.

`band_features()` reports named-band absolute/relative powers, normalization
range, amplitude-squared units and coverage. Incomplete bands/reference ranges
remain unavailable; zero-power relative values are unavailable rather than zero.
`coherence_matrix()` returns symmetric, bounded magnitude-squared coherence for
at least two nonconstant channels and two overlapping Welch segments, with an
explicit window and output-size limit. It matches SciPy's estimator in tests.

Scalp spectral coupling can reflect volume conduction and common reference.
It does not establish a neural source or causal network.

## EEG and event processing

`common_average_reference()` and `bipolar_reference()` transform known electrical
channels. Exclude identified bad channels explicitly before common averaging.
`epoch()` accepts integer event sample indices, inclusive start/end times rounded
to nearest samples, and optional inclusive baseline interval. It rejects any
out-of-range epoch rather than silently dropping trials. `Epochs` preserves
channels, unit, reference, event indices, modality and timing; `.average()`
computes an event average with its trial count and epoch start time in metadata.

`phase_locking_value()` computes pairwise temporal PLV using Hilbert phase.
Pass suitable narrowband signals and remove filter edges first. Constant signals
fail. `bad_channel_candidates()` flags flatline/high-variance candidates only;
it is not a calibrated bad-channel detector. `handle_bad_channels()` accepts
explicit reviewed labels and either drops them or uses MNE spherical-spline
interpolation on a template/supplied montage. Interpolation requires at least
four good channels, records its method and affected labels, and estimates missing
scalp values rather than recovering physiological truth. Review electrode
coverage, sphere-fit assumptions and acquisition reference before using it.

`ica_remove()` requires MNE and scikit-learn. It fits reproducible FastICA and
removes only explicitly supplied, reviewed component indices. No component is
classified automatically as an artifact; desired activity can be removed.
Insufficient samples, invalid rank/index and reached iteration limits fail.
Choose filtering, channel selection and component count scientifically before
fitting; ICA does not establish independent anatomical neural sources.

## EMG and peripheral descriptions

`emg_features()` reports RMS, MAV, waveform length, integrated EMG, zero crossings,
slope sign changes, median and mean PSD frequencies. Crossing thresholds use the
signal's amplitude units. Integrated EMG uses sum(abs(x))/sfreq. Zero power gives
unavailable frequency values. These frequency features alone do not establish
muscle fatigue.

`activation_intervals()` uses a trailing RMS envelope and explicit threshold,
window and minimum duration. Initial incomplete windows are excluded. Its
half-open intervals are threshold candidates, not validated physiological onsets.

`peak_intervals()` locates configurable ECG/PPG/EOG peak candidates on signals
that the caller has preprocessed. Returned intervals and reciprocal mean rate
need peak review. This is not an automatic QRS/blink detector, arrhythmia decision,
blood-pressure estimate, oxygen-saturation measurement or validated heart-rate
monitor.

`eda_components()` separates an explicit lowpass tonic approximation from its
residual in conductance units. The residual is not deconvolved sudomotor activity
and can be negative. `adaptive_cancel()` implements deterministic normalized LMS
with an explicit reference, taps and learning rate. History binds reference data
SHA-256, shape/dtype, metadata, prior processing and positional channel mapping;
reference/acquisition time synchronization remains the caller's responsibility. It it may also remove desired
activity correlated with that reference. It is not automatic artifact removal.

## Interchange and parsing limits

`save_signal()` writes a versioned NPZ with numeric arrays and strict JSON metadata.
`load_signal()` disables pickle, bounds compressed/uncompressed sizes and declared
NPY allocations including float64 expansion, and rejects unexpected archive members. Saving exclusively creates
files and preserves previous outputs. `save_hdf5()`/`load_hdf5()` use a versioned
engine schema, preserve provenance, reject external/virtual datasets and bound
expanded sample allocation. They require h5py; generic HDF5 is not silently
interpreted as engine data.

`load_mat()` accepts explicit data key, sampling frequency, labels, modality,
unit and reference for numeric MATLAB v4/v5/v7.2 matrices. It checks file size
and declared shape/class before loading the selected matrix; its conservative
allocation budget reserves complex-double storage even for integer inputs. MATLAB v7.3 is not
silently treated as that format. `load_mne()` supports electrical channels in
EDF/EDF+, BDF, GDF and FIF through MNE, explicitly converts volts to uV and retains
selected channel labels, bad-channel names and annotations. EDF/BDF channel types
are inferred from labels by MNE, whose unknown labels can default to EEG; users
must verify source channel metadata and biological identity. It rejects absent
requested modality and oversize selected samples. Acquisition reference is not
inferred. Generic format parsers are not a security sandbox; only parse trusted
files, and apply OS resource limits when processing adversarial inputs. General
HDF5/MAT parsing has not undergone fuzzing or an independent security audit.

## Electrode and event-average visualization

`scalp_positions()` resolves exact EEG labels with an MNE built-in montage or
caller-provided `DigMontage`, returning head coordinates in metres. The default
selects MNE's current 10–20 template name, with a legacy-name fallback for older
MNE versions. Unknown labels fail. Template electrodes approximate a standard
head; they are not individual digitization or intracranial positions.

`plot_topomap(signal, values, value_unit=...)` plots explicitly unit-labelled
channel scalars with local spatial interpolation. `plot_montage()` shows selected
sensors in 2D or 3D. Neither image is neural-source localization. An interpolated
value between electrodes is not another measured channel. `plot_evoked()` plots
an `Epochs` trial average, optional pointwise Student-t confidence intervals, the
event time and original amplitude unit. Intervals assume independent trials and
are not participant-level or simultaneous inference; correlated trials violate
the assumption. No component is classified automatically as P300 or another ERP.

## Optional BIDS and XDF workflows

`load_bids(bids_path, modality="eeg")` requires MNE-BIDS and an explicit `BIDSPath`.
It preserves channel names, sample rate, signal reference, bad-channel labels,
annotations and recording JSON/channel/event/electrode/coordinate sidecars with
source checksums. MNE electrical volt values are explicitly converted to uV.
Selected sample count and sidecar size are bounded. Participant demographics are
not copied into signal exports; the dataset remains in its source directory.
This adapter is not a complete BIDS validator or dataset anonymizer.

`load_xdf(path, stream_id=..., modality=..., unit=...)` requires pyxdf and explicitly
selects one regular numeric stream. A strict chunk/header preflight bounds sample
counts and float64 expansion before parsing. The adapter refuses partial data
from pyxdf's tolerant corruption recovery. Complete original timestamps, clock
offset measurements and raw stream/container metadata are retained; no clock
synchronization, reset correction, de-jittering or resampling occurs. Timestamp
intervals must match the nominal sample rate within an explicit tolerance.
Irregular streams fail and require a separate specified synchronization/resampling
workflow. Complete channel labels or explicit labels are required, and declared
channel units must agree with the caller's unit. Compressed `.xdfz`, irregular
marker streams and implicit multi-device clock alignment are unsupported.
Long timestamp lists may exceed the NPZ/HDF5 metadata read limit; increasing that
limit or an alternate timestamp-aware storage scheme must be explicit.

Actual synthetic EDF-backed BIDS and binary XDF files exercise parsing, sidecar
reference/annotation/unit preservation, discontinuity rejection and malformed
sample-count handling. Offscreen image tests draw real MNE scalp maps, montages
and event averages. These are synthetic interoperability checks, not broad
real-dataset compatibility or independent scientific validation.

## Optional peripheral library workflows

`process_peripheral(signal, channel=...)` uses NeuroKit2 to run an explicitly
selected ECG, PPG, EDA or vertical-EOG research pipeline. Electrical channels are
converted to mV, conductance to uS, and PPG must use arbitrary units. ECG defaults
to the NeuroKit method, PPG to Elgendi, and EDA to NeuroKit. Vertical EOG uses
explicit NeuroKit cleaning and MNE peak detection and requires positive blink
polarity. Additional documented ECG methods are Pan–Tompkins (1985) and Hamilton
(2002), selected by their NeuroKit method identifiers. These method names refer
to external implementations, not new clinical evidence collected by this project.

The engineering wrapper requires integer sampling rates (ECG at least 100 Hz,
PPG 25 Hz, EDA 10 Hz and EOG 50 Hz), 10 seconds of data and no more than 1,000,000
samples. These are wrapper operating limits, not proven physiological accuracy
thresholds. Constant signals fail. The original NeuroKit sample table and event
information are preserved; missing/unavailable derived values are not changed to
zero. `PeripheralResult.summary()` encodes nonfinite missing values as JSON null
and reports finite-rate coverage separately. Source hash, units, reference,
metadata, processing history, exact library version/method and emitted warnings
are retained. Library quality columns are heuristics, not evidence of clinical
quality. Rate descriptions require reviewed event identity.

The pipeline is offline: filters and interpolated rates may be acausal. It has
not been validated for live monitoring or prospective diagnosis. Synthetic tests
exercise ECG/PPG known simulated rate, conductance scaling/decomposition and
positive mathematical EOG pulse timing. Those checks do not establish real-world
sensitivity, specificity, physiological ground truth, clinical accuracy or
independent verification. Do not infer disease, diagnosis, blood pressure,
oxygen saturation or a clinical decision from these outputs.

Automatic ASR, automatic artifact classification, clinically validated peripheral
pipelines, anatomical source reconstruction and physical acquisition are not
claimed by this package. Other modules have their own acceptance status.

## Reproduce verification

From the repository root with development, MNE, scikit-learn, PyWavelets and
h5py, MNE-BIDS, pyxdf and NeuroKit2 installed:

```sh
python -m pytest tests/test_engine.py tests/test_engine_visualization.py tests/test_engine_interchange.py tests/test_engine_physiology.py tests/test_engine_connectivity.py -ra
python benchmarks/verify_engine.py --output local-results/engine-verification.json
python examples/engine_workflow.py --output local-results/engine-example.npz
```

Tests include analytical power/frequency targets, matched SciPy filters, causal
chunk equivalence, explicit anti-alias control, interpolation/epoch limits,
wavelet localization/reconstruction, ICA reconstruction and removal, typed
interchange, malicious shape headers and external HDF5 links. Shared NumPy/SciPy
and MNE comparisons are interoperability evidence, not fully independent
scientific validation. No real-world peripheral cohort or independent review
has been performed for this additive engine.
