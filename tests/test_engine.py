"""Analytical, matched-reference and malformed-input checks for additive engine."""

import json
import zipfile

import numpy as np
import pytest
from scipy import signal as sp
from scipy.integrate import trapezoid
from biosignal_lab.engine import (
    Signal,
    FilterSpec,
    StreamingFilter,
    filter_signal,
    resample_signal,
    detrend_signal,
    normalize_signal,
    welch_psd,
    fft_spectrum,
    stft,
    spectrogram,
    multitaper_psd,
    spectral_entropy,
    integrate_band,
    common_average_reference,
    bipolar_reference,
    epoch,
    phase_locking_value,
    bad_channel_candidates,
    emg_features,
    activation_intervals,
    peak_intervals,
    eda_components,
    adaptive_cancel,
    save_signal,
    load_signal,
    load_mat,
    load_mne,
)


def tone(frequency=10, sfreq=250, duration=8, amplitude=10, modality="eeg"):
    t = np.arange(int(sfreq * duration)) / sfreq
    return Signal(
        (amplitude * np.sin(2 * np.pi * frequency * t))[None],
        sfreq,
        ("Cz",),
        modality,
        metadata={"source": "analytic sine"},
        reference="synthetic_zero",
    )


def test_signal_copy_units_and_metadata():
    original = np.ones((1, 10))
    source = {"a": [1]}
    s = Signal(original, 100, ("A",), metadata=source)
    original[:] = 4
    source["a"].append(2)
    assert np.all(s.data == 1) and s.metadata["a"] == [1]
    with pytest.raises(ValueError):
        s.data[0, 0] = 2
    assert s.to_unit("V").data[0, 0] == pytest.approx(1e-6)
    assert s.to_unit("V").to_unit("uV").unit == "uV"
    with pytest.raises(ValueError, match="Incompatible"):
        s.to_unit("uS")
    conductance = Signal(original, 100, ("A",), "eda", "uS")
    np.testing.assert_allclose(conductance.to_unit("S").data, original * 1e-6)


@pytest.mark.parametrize(
    "data,sfreq,channels,unit",
    [
        ([[np.nan]], 100, ("A",), "uV"),
        ([[1]], 0, ("A",), "uV"),
        ([[1], [2]], 100, ("A", "A"), "uV"),
        ([[1]], 100, ("",), "uV"),
        ([[1]], 100, ("A",), "unknown"),
    ],
)
def test_signal_rejects_ambiguous_input(data, sfreq, channels, unit):
    with pytest.raises(ValueError):
        Signal(data, sfreq, channels, unit=unit)


@pytest.mark.parametrize("family", ["butter", "cheby1", "cheby2", "bessel", "ellip", "fir"])
@pytest.mark.parametrize("phase", ["zero", "causal"])
def test_filters_match_scipy_and_preserve_scientific_metadata(family, phase):
    s = tone()
    spec = FilterSpec(
        family=family, kind="lowpass", cutoff=20.0, order=31 if family == "fir" else 4, phase=phase
    )
    out = filter_signal(s, spec)
    form, coeff = spec.coefficients(s.sfreq)
    if form == "sos":
        expected = (
            sp.sosfilt(coeff, s.data, axis=-1)
            if phase == "causal"
            else sp.sosfiltfilt(
                coeff, s.data, axis=-1, padlen=out.history[-1]["parameters"]["pad_samples"]
            )
        )
    else:
        expected = (
            sp.lfilter(coeff, [1.0], s.data, axis=-1)
            if phase == "causal"
            else sp.filtfilt(coeff, [1.0], s.data, axis=-1, padlen=3 * len(coeff))
        )
    np.testing.assert_allclose(out.data, expected)
    assert out.metadata == s.metadata and out.reference == s.reference and out.unit == s.unit
    assert out.history[-1]["operation"] == "filter"


@pytest.mark.parametrize("family", ["butter", "fir"])
def test_causal_chunking_equals_one_shot_and_reset(family):
    data = np.random.default_rng(42).normal(size=(3, 1000))
    spec = FilterSpec(
        family=family,
        kind="bandpass",
        cutoff=(5, 40),
        order=31 if family == "fir" else 4,
        phase="causal",
    )
    stateful = StreamingFilter(spec, 250, 3)
    chunks = [
        stateful.process(data[:, :17]),
        stateful.process(data[:, 17:513]),
        stateful.process(data[:, 513:]),
    ]
    expected = filter_signal(Signal(data, 250, ("a", "b", "c")), spec).data
    np.testing.assert_allclose(np.concatenate(chunks, axis=1), expected, rtol=1e-12, atol=1e-12)
    stateful.reset()
    np.testing.assert_allclose(stateful.process(data), expected)
    with pytest.raises(ValueError):
        stateful.process(np.ones((2, 20)))


def test_filters_reject_invalid_parameters_and_short_zero_phase():
    for spec in [
        FilterSpec(cutoff=(40, 1)),
        FilterSpec(cutoff=(1, 125)),
        FilterSpec(family="bad"),
        FilterSpec(order=0),
        FilterSpec(family="fir", order=4),
        FilterSpec(quality=np.nan),
    ]:
        with pytest.raises(ValueError):
            filter_signal(tone(), spec)
    with pytest.raises(ValueError, match="more than"):
        filter_signal(Signal(np.ones((1, 5)), 250, ("A",)), FilterSpec())
    with pytest.raises(ValueError):
        StreamingFilter(FilterSpec(), 250, 1)


def test_notch_attenuates_known_tone():
    s = tone(50, duration=20)
    out = filter_signal(s, FilterSpec(kind="notch", cutoff=50.0))
    assert np.std(out.data[:, 500:-500]) < np.std(s.data) * 0.02


def test_resampling_antialias_and_provenance():
    s = tone(80, sfreq=500, duration=10)
    out = resample_signal(s, 100)
    assert out.sfreq == 100 and out.data.shape == (1, 1000)
    assert np.std(out.data[:, 50:-50]) < 0.01 * np.std(s.data)
    assert out.metadata == s.metadata and out.history[-1]["parameters"]["anti_alias"]
    low = resample_signal(tone(10, sfreq=500), 100)
    assert np.std(low.data[:, 50:-50]) == pytest.approx(10 / np.sqrt(2), rel=0.005)


def test_detrend_normalize_and_constant_failure():
    ramp = Signal(np.arange(100, dtype=float)[None], 100, ("ramp",))
    assert np.max(abs(detrend_signal(ramp).data)) < 1e-12
    s = normalize_signal(tone())
    assert s.unit == "a.u." and s.data.std() == pytest.approx(1.0)
    with pytest.raises(ValueError, match="zero dispersion"):
        normalize_signal(Signal(np.ones((1, 20)), 20, ("constant",)))


def test_spectral_estimates_analytical_power_frequency_and_entropy():
    s = tone()
    f, p = welch_psd(s)
    assert f[np.argmax(p[0])] == 10
    assert integrate_band(f, p, 8, 13)[0] == pytest.approx(50.0, rel=0.001)
    assert trapezoid(p[0], f) == pytest.approx(50.0, rel=0.001)
    freq, amp = fft_spectrum(s)
    assert amp[0, np.argmax(amp[0])] == pytest.approx(10)
    assert freq[np.argmax(amp[0])] == 10
    f, p = multitaper_psd(s)
    assert trapezoid(p[0], f) == pytest.approx(50.0, rel=0.005)
    assert spectral_entropy(np.ones(8)) == pytest.approx(1.0)
    assert spectral_entropy(np.r_[1.0, np.zeros(7)]) == pytest.approx(0.0)
    with pytest.raises(ValueError):
        integrate_band(f, p, 100, 200)
    with pytest.raises(ValueError):
        spectral_entropy(np.zeros(8))


def test_stft_and_spectrogram_localize_tone_without_boundary_padding():
    s = tone(20)
    f, t, z = stft(s)
    f2, t2, p = spectrogram(s)
    assert np.all(f[np.argmax(abs(z[0]), axis=0)] == 20)
    assert np.all(f2[np.argmax(p[0], axis=0)] == 20)
    np.testing.assert_allclose(t, t2)
    assert t[0] == 1 and t[-1] <= s.duration_s - 1


def test_referencing_and_epochs_baseline_recover_evoked_response():
    s = Signal(np.vstack([np.arange(1000), np.arange(1000) + 2]), 100, ("a", "b"), reference="old")
    car = common_average_reference(s)
    np.testing.assert_allclose(car.data.mean(axis=0), 0)
    assert car.reference == "common_average"
    bip = bipolar_reference(s, [("a", "b")])
    np.testing.assert_allclose(bip.data, -2)
    trials = epoch(s, np.array([100, 400]), tmin=-0.1, tmax=0.2, baseline=(-0.1, 0))
    assert trials.data.shape == (2, 2, 31)
    np.testing.assert_allclose(trials.data[..., :11].mean(axis=-1), 0, atol=1e-12)
    assert trials.average().metadata["evoked_trials"] == 2
    with pytest.raises(ValueError, match="fit inside"):
        epoch(s, np.array([1]), tmin=-0.1)
    with pytest.raises(ValueError):
        epoch(s, np.array([100.5]))


def test_plv_phase_shift_and_bad_channel_candidates():
    t = np.arange(2000) / 250
    s = Signal(
        np.array([np.sin(2 * np.pi * 10 * t), np.sin(2 * np.pi * 10 * t + 0.7)]), 250, ("a", "b")
    )
    np.testing.assert_allclose(phase_locking_value(s), 1, atol=1e-10)
    flat = Signal(np.zeros((1, 20)), 100, ("a",))
    assert bad_channel_candidates(flat)["a"] == ["flatline_candidate"]
    with pytest.raises(ValueError):
        phase_locking_value(flat)


def test_emg_features_analytic_sine_and_activation_boundaries():
    s = tone(50, sfreq=1000, duration=2, modality="emg")
    features = emg_features(s, threshold=0.01)[0]
    assert features["rms"] == pytest.approx(10 / np.sqrt(2))
    assert features["mean_frequency_hz"] == pytest.approx(50.0, abs=0.001)
    assert features["median_frequency_hz"] == pytest.approx(50.0, abs=0.001)
    assert 190 <= features["zero_crossings"] <= 200
    intervals = activation_intervals(s, threshold=1, window_s=0.05)
    assert len(intervals) == 1 and intervals[0]["start_s"] == 0.049 and intervals[0]["stop_s"] == 2


def test_peripheral_candidates_no_diagnostic_claim():
    s = tone(1, sfreq=100, duration=10, modality="ppg")
    peaks = peak_intervals(s, prominence=5, min_distance_s=0.5)[0]
    assert peaks["mean_rate_per_min"] == pytest.approx(60.0)
    assert peaks["review_required"]
    eda = Signal(2 + 0.2 * np.sin(np.arange(10000)[None] / 100), 100, ("eda",), "eda", "uS")
    tonic, residual = eda_components(eda)
    np.testing.assert_allclose(tonic.data + residual.data, eda.data)
    assert tonic.unit == residual.unit == "uS"
    with pytest.raises(ValueError):
        eda_components(Signal(eda.data, 100, ("eda",), "eda", "uV"))


def test_adaptive_reference_cancellation_reduces_known_interference():
    rng = np.random.default_rng(4)
    noise = rng.normal(size=(1, 10000))
    desired = tone(10, sfreq=250, duration=40, amplitude=0.2)
    contaminated = Signal(desired.data + 3 * noise, 250, ("Cz",))
    cleaned, weights = adaptive_cancel(
        contaminated, Signal(noise, 250, ("reference",)), taps=4, step=0.1
    )
    assert np.std(cleaned.data[:, 1000:] - desired.data[:, 1000:]) < 0.1
    assert weights.shape == (1, 4)


def test_npz_roundtrip_no_overwrite_and_archive_limit(tmp_path):
    s = filter_signal(tone(), FilterSpec(kind="lowpass", cutoff=30))
    path = tmp_path / "signal.npz"
    save_signal(s, path)
    restored = load_signal(path)
    np.testing.assert_array_equal(restored.data, s.data)
    assert (
        restored.channels == s.channels
        and restored.unit == s.unit
        and restored.history == s.history
    )
    with pytest.raises(FileExistsError):
        save_signal(s, path)
    with pytest.raises(ValueError):
        load_signal(path, max_bytes=100)
    invalid = tmp_path / "invalid.npz"
    with zipfile.ZipFile(invalid, "w") as z:
        z.writestr("../data.npy", "bad")
    with pytest.raises(ValueError):
        load_signal(invalid)


def test_mat_adapter_explicit_units(tmp_path):
    from scipy.io import savemat

    path = tmp_path / "signal.mat"
    savemat(path, {"samples": np.ones((2, 100))})
    s = load_mat(path, data_key="samples", sfreq=100, channels=("a", "b"), modality="eeg", unit="V")
    assert s.unit == "V" and s.to_unit("uV").data[0, 0] == 1e6


def test_mne_fif_adapter_channel_selection_units_and_annotations(tmp_path):
    mne = pytest.importorskip("mne")
    info = mne.create_info(["Cz", "muscle"], 100, ["eeg", "emg"])
    raw = mne.io.RawArray(
        np.vstack([np.ones(1000) * 1e-6, np.ones(1000) * 2e-6]), info, verbose="ERROR"
    )
    raw.set_annotations(mne.Annotations([1], [0.5], ["test"]))
    path = tmp_path / "test_raw.fif"
    raw.save(path, overwrite=False, verbose="ERROR")
    s = load_mne(path, modality="emg")
    np.testing.assert_allclose(s.data, 2, rtol=1e-6)
    assert (
        s.channels == ("muscle",)
        and s.unit == "uV"
        and s.metadata["annotations"][0]["description"] == "test"
    )


def test_explicit_gap_repair_rejects_boundaries_and_long_gaps():
    from biosignal_lab.engine import repair_missing

    data = np.arange(100, dtype=float)[None]
    data[0, 30:32] = np.nan
    s = repair_missing(data, 100, ("a",), max_gap_s=0.02)
    np.testing.assert_allclose(s.data, np.arange(100)[None])
    assert s.history[-1]["operation"] == "interior_linear_interpolation"
    with pytest.raises(ValueError):
        repair_missing(data, 100, ("a",), max_gap_s=0.01)
    data[0, 0] = np.nan
    with pytest.raises(ValueError):
        repair_missing(data, 100, ("a",))


def test_wavelet_known_frequency_and_dwt_reconstruction():
    pywt = pytest.importorskip("pywt")
    from biosignal_lab.engine import wavelet_transform, discrete_wavelet

    s = tone(10, duration=4)
    f, coefficients = wavelet_transform(s, frequencies=np.arange(5.0, 16.0))
    assert f[np.argmax(np.mean(abs(coefficients[:, 0, 200:-200]) ** 2, axis=-1))] == pytest.approx(
        10, abs=1.0
    )
    pieces = discrete_wavelet(s, wavelet="db4", level=3)
    np.testing.assert_allclose(pywt.waverec(pieces, "db4", axis=-1), s.data, atol=1e-12)
    with pytest.raises(ValueError):
        discrete_wavelet(s, level=100)


def test_hdf5_roundtrip_and_external_dataset_rejected(tmp_path):
    h5py = pytest.importorskip("h5py")
    from biosignal_lab.engine import save_hdf5, load_hdf5

    s = tone()
    path = tmp_path / "signal.h5"
    save_hdf5(s, path)
    restored = load_hdf5(path)
    np.testing.assert_array_equal(restored.data, s.data)
    assert restored.unit == s.unit and restored.reference == s.reference
    with pytest.raises((FileExistsError, OSError)):
        save_hdf5(s, path)
    with pytest.raises(ValueError):
        load_hdf5(path, max_bytes=10)
    external = tmp_path / "external.h5"
    with h5py.File(external, "x") as target:
        target["data"] = h5py.ExternalLink(str(path), "data")
    with pytest.raises(ValueError):
        load_hdf5(external)


def test_mne_ica_explicit_empty_removal_reconstructs_and_preserves_units():
    pytest.importorskip("sklearn")
    pytest.importorskip("mne")
    from biosignal_lab.engine import ica_remove

    rng = np.random.default_rng(7)
    sources = rng.laplace(size=(2, 2000))
    mixed = np.array([[1.0, 0.5], [0.3, 1.0]]) @ sources
    s = Signal(mixed, 250, ("a", "b"))
    result = ica_remove(s, exclude=[], n_components=2)
    np.testing.assert_allclose(result.data, s.data, atol=1e-10)
    assert result.unit == "uV" and result.history[-1]["parameters"]["review_required"]
    removed = ica_remove(s, exclude=[0], n_components=2)
    assert np.std(removed.data) < np.std(s.data)
    with pytest.raises(ValueError):
        ica_remove(s, exclude=[99], n_components=2)


def test_malicious_npz_declared_shape_is_rejected_before_allocation(tmp_path):
    import io

    stream = io.BytesIO()
    np.lib.format.write_array_header_1_0(
        stream, {"descr": "<f8", "fortran_order": False, "shape": (1000000000000,)}
    )
    path = tmp_path / "huge.npz"
    with zipfile.ZipFile(path, "w") as target:
        target.writestr("data.npy", stream.getvalue())
        target.writestr("metadata.npy", stream.getvalue())
    with pytest.raises(ValueError, match="allocation limit"):
        load_signal(path)


def test_epoch_resource_limit_precedes_offset_allocation():
    with pytest.raises(ValueError, match="resource limit"):
        epoch(tone(), [100], tmin=-1e15, tmax=1e15)
    result = epoch(tone(modality="ecg"), np.array([200], dtype=np.uint64), tmin=-0.1, tmax=0.1)
    assert result.average().modality == "ecg"


def test_signal_rejects_complex_values_instead_of_discarding_imaginary_part():
    with pytest.raises(ValueError, match="complex"):
        Signal(np.ones((1, 10), dtype=complex) * (1 + 2j), 100, ("a",))


def test_edf_adapter_requires_explicit_mne_type_inference(monkeypatch):
    mne = pytest.importorskip("mne")
    raw = mne.io.RawArray(
        np.ones((2, 1000)) * 1e-6,
        mne.create_info(["Fz", "Chin"], 100, ["eeg", "emg"]),
        verbose="ERROR",
    )

    def reader(*args, **kwargs):
        assert kwargs["infer_types"] is True
        return raw.copy()

    monkeypatch.setattr(mne.io, "read_raw_edf", reader)
    s = load_mne("synthetic.edf", modality="emg")
    assert s.channels == ("Chin",) and s.metadata["typing_note"]


def test_epoch_average_retains_processing_history_and_events():
    s = filter_signal(tone(modality="ecg"), FilterSpec(kind="lowpass", cutoff=30))
    avg = epoch(s, [200, 500], -0.1, 0.1).average()
    assert avg.history[0]["operation"] == "filter"
    assert avg.history[1]["operation"] == "event_average"
    assert avg.history[1]["parameters"]["events"] == [200, 500]


def test_spectral_overflow_is_rejected_and_entropy_is_scale_invariant():
    assert spectral_entropy(np.full(8, 1e308)) == pytest.approx(1.0)
    huge = Signal(np.full((1, 1000), 1e308), 100, ("extreme",))
    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(ValueError, match="overflow"):
            welch_psd(huge)
        with pytest.raises(ValueError, match="overflow"):
            normalize_signal(huge)
    with pytest.raises(ValueError):
        integrate_band([0.0, 1.0], 2.0, 0.0, 1.0)
