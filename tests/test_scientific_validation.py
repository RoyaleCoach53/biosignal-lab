"""Numerical verification against known physical/math ground truths.

These tests verify algorithmic behavior only: they are NOT clinical validation.
"""
import numpy as np
import pandas as pd
import pytest
from biosignal_lab.analysis import (compute_psd, band_powers, emg_descriptors,
                                     hjorth_parameters, pairwise_coherence,
                                     time_frequency_psd, detect_artifacts)
from biosignal_lab.models import Recording, AnalysisConfig
from biosignal_lab.pipeline import analyze, default_config
from biosignal_lab.preprocessing import fill_short_gaps
from biosignal_lab.io import read_csv, read_edf


def sine(freq, amp=10, fs=250, seconds=60):
    t = np.arange(int(fs * seconds)) / fs
    return amp * np.sin(2 * np.pi * freq * t)


@pytest.mark.parametrize('f,band', [(2, 'delta'), (6, 'theta'), (10, 'alpha'),
                                   (20, 'beta'), (35, 'gamma'), (42, 'gamma')])
def test_known_sine_power(f, band):
    # 10 µV peak sine => A²/2 = 50 µV². Loss <3% away from band boundaries.
    rec = Recording(sine(f)[None], 250, ('EEG',))
    result = analyze(rec)
    assert result.band_powers[0][f'{band}_uv2'] == pytest.approx(50., rel=.03)


@pytest.mark.parametrize('freq', [10, 20, 35, 42])
def test_spectral_peak_correct_frequency(freq):
    f, psd = compute_psd(sine(freq)[None], 250)
    assert f[int(np.argmax(psd[0]))] == pytest.approx(freq, abs=.26)


def test_welch_total_power_matches_variance_for_white_noise():
    rng = np.random.default_rng(100)
    x = rng.normal(0, 5., 250 * 200)
    f, psd = compute_psd(x[None], 250)
    from scipy.integrate import trapezoid
    spectral_power = trapezoid(psd[0], f)
    assert spectral_power == pytest.approx(np.var(x), rel=.08)


def test_amplitude_scaling_power_and_units():
    f, p = compute_psd(sine(10, amp=3)[None], 250)
    _, q = compute_psd(sine(10, amp=6)[None], 250)
    assert band_powers(f, q, ('x',))[0]['alpha_uv2'] == pytest.approx(
        4 * band_powers(f, p, ('x',))[0]['alpha_uv2'], rel=1e-8)


def test_gamma_not_suppressed_by_default_lowpass():
    result = analyze(Recording(sine(42)[None], 250, ('x',)))
    assert result.config.lowpass_hz is None
    assert result.band_powers[0]['gamma_uv2'] > 48


def test_gamma_unavailable_below_nyquist():
    f, p = compute_psd(sine(10, fs=80)[None], 80)
    row = band_powers(f, p, ('x',))[0]
    assert row['gamma_uv2'] is None
    assert row['gamma_relative'] is None
    assert row['gamma_coverage'] == pytest.approx(2/3)


def test_delta_measurement_warns_if_highpass_clips_band():
    rec = Recording(sine(2)[None], 250, ('EEG',))
    cfg = AnalysisConfig(highpass_hz=1., lowpass_hz=40.)
    result = analyze(rec, cfg)
    assert any('delta' in w.lower() for w in result.warnings)
    assert any('gamma' in w.lower() for w in result.warnings)


def test_emg_high_frequency_preserved_at_500_hz_sample_rate():
    fs = 500
    data = sine(200, amp=100, fs=fs, seconds=10)
    result = analyze(Recording(data[None], fs, ('EMG1',), modality='emg'))
    qc = result.channel_metrics[0]
    assert result.config.lowpass_hz is None
    assert qc['emg_rms_uv'] == pytest.approx(100 / np.sqrt(2), rel=.01)
    assert qc['emg_median_frequency_hz'] == pytest.approx(200, abs=2)
    assert any('1000' in w for w in result.warnings)


def test_emg_standard_rate_2000_preserves_200_hz():
    fs = 2000
    data = sine(200, amp=100, fs=fs, seconds=10)
    result = analyze(Recording(data[None], fs, ('EMG1',), modality='emg'))
    assert result.config.lowpass_hz == 450
    assert result.channel_metrics[0]['emg_rms_uv'] == pytest.approx(100/np.sqrt(2), rel=.02)


def test_hjorth_sine_approximates_angular_frequency():
    fs = 500
    m = hjorth_parameters(sine(10, amp=10, fs=fs), fs)
    assert m['hjorth_activity_uv2'] == pytest.approx(50., rel=.001)
    assert m['hjorth_mobility_per_s'] == pytest.approx(2 * np.pi * 10, rel=.01)
    assert m['hjorth_complexity'] == pytest.approx(1, rel=.02)


def test_emg_descriptors_known_mav_and_rms():
    x = sine(80, amp=100, fs=2000)
    m = emg_descriptors(x, 2000)
    assert m['emg_rms_uv'] == pytest.approx(100/np.sqrt(2), rel=.005)
    assert m['emg_mav_uv'] == pytest.approx(200/np.pi, rel=.01)
    assert m['emg_median_frequency_hz'] == pytest.approx(80, abs=2)


def test_time_frequency_transient_is_localized():
    fs = 250
    x = sine(10, fs=fs, seconds=20)
    x[int(10*fs):int(12*fs)] += 15 * sine(30, fs=fs, seconds=2)
    f, t, spec = time_frequency_psd(x, fs)
    j = np.argmin(np.abs(f - 30))
    assert t[np.argmax(spec[j])] == pytest.approx(11, abs=1)


def test_coherence_correlated_and_uncorrelated_controls():
    rng = np.random.default_rng(222)
    x = rng.normal(size=10000)
    y = rng.normal(size=10000)
    f, independent = pairwise_coherence(x, y, 250)
    _, duplicate = pairwise_coherence(x, x, 250)
    assert np.mean(independent[(f > 5) & (f < 90)]) < .15
    assert np.median(duplicate) > .999


def test_artifact_known_burst_detected():
    fs = 250
    x = sine(10, amp=5, fs=fs, seconds=20)
    x[5*fs+10:5*fs+20] += 250
    flagged = detect_artifacts(x[None], fs, ('x',), window_s=1., threshold_mad=8,
                               flatline_tolerance_uv=.15)
    assert any(row['start_s'] <= 5 < row['end_s'] for row in flagged)


def test_long_missing_gap_rejected_despite_low_missing_fraction():
    x = sine(10, fs=250, seconds=30)[None]
    x[0, 100:200] = np.nan   # 100 samples (0.4s), just 1.33% missing
    with pytest.raises(ValueError, match='maximum interpolation duration'):
        analyze(Recording(x, 250, ('x',)))


def test_short_interior_gap_allowed_with_explicit_warning():
    x = sine(10, fs=250, seconds=10)[None]
    x[0, 100:103] = np.nan
    result = analyze(Recording(x, 250, ('x',)))
    assert any('interpolated' in s for s in result.warnings)


def test_boundary_gap_is_not_extrapolated():
    x = np.arange(1000, dtype=float)[None]
    x[0, 0] = np.nan
    with pytest.raises(ValueError, match='boundary'):
        fill_short_gaps(x, max_missing_fraction=.05)


def test_csv_declared_sfreq_vs_timebase_consistency(tmp_path):
    path = tmp_path/'time.csv'
    pd.DataFrame({'time_s':np.arange(1000)/250, 'EEG':np.ones(1000)}).to_csv(path, index=False)
    with pytest.raises(ValueError, match='disagrees'):
        read_csv(path, sfreq=200, time_column='time_s')
    rec = read_csv(path, sfreq=250, time_column='time_s')
    assert rec.duration_s == 4


def test_irregular_csv_timestamps_rejected(tmp_path):
    times = np.arange(1000) / 250
    times[250:] += .008
    path = tmp_path/'irregular.csv'
    pd.DataFrame({'time_s':times, 'EEG':np.ones(1000)}).to_csv(path, index=False)
    with pytest.raises(ValueError, match='Irregular'):
        read_csv(path, sfreq=250, time_column='time_s')


def test_edf_modality_separation(monkeypatch):
    mne = pytest.importorskip('mne')
    info = mne.create_info(['EEG Fz', 'EMG Chin'], sfreq=250, ch_types=['eeg', 'emg'])
    mock_raw = mne.io.RawArray(np.vstack([np.full(2000,10e-6), np.full(2000, 100e-6)]),
                               info, verbose='ERROR')
    def mock_reader(*a, **k):
        assert k['infer_types'] is True
        return mock_raw.copy()
    monkeypatch.setattr(mne.io, 'read_raw_edf', mock_reader)
    eeg = read_edf('dummy.edf', modality='eeg')
    emg = read_edf('dummy.edf', modality='emg')
    assert eeg.channels == ('EEG Fz',)
    assert emg.channels == ('EMG Chin',)
    assert eeg.data_uv[0,10] == pytest.approx(10)
    assert emg.data_uv[0,10] == pytest.approx(100)


def test_nonfinite_filter_cutoffs_rejected():
    for c in [AnalysisConfig(highpass_hz=np.nan), AnalysisConfig(lowpass_hz=np.inf),
              AnalysisConfig(window_s=np.nan), AnalysisConfig(max_gap_s=np.inf)]:
        with pytest.raises(ValueError):
            c.validate(250, 10000)


def test_welch_psd_independently_matches_mne():
    """Independent library check: input units convert µV to V and back."""
    mne = pytest.importorskip('mne')
    rng = np.random.default_rng(909)
    x = sine(10, amp=12, seconds=20) + sine(35, amp=5, seconds=20) + rng.normal(0, 1, 5000)
    fs = 250
    f, ours = compute_psd(x[None], fs, window_s=2)
    reference, ref_f = mne.time_frequency.psd_array_welch(
        x*1e-6, sfreq=fs, n_fft=500, n_per_seg=500, n_overlap=250,
        window='hann', average='mean', verbose='ERROR')
    np.testing.assert_allclose(f, ref_f)
    np.testing.assert_allclose(ours[0], reference*1e12, rtol=1e-7, atol=1e-10)


def test_real_edf_file_format_round_trip(tmp_path):
    """An actual EDF file with known synthetic amplitudes and mixed signal types."""
    mne = pytest.importorskip('mne')
    fs = 250
    n_records = 10
    labels = ['EEG Fz', 'EMG Chin']
    fields = [('0',8),('anonymous',80),('synthetic unit test',80),('01.01.24',8),
              ('01.01.01',8),(str(256+len(labels)*256),8),('EDF+C',44),
              (str(n_records),8),('1',8),(str(len(labels)),4)]
    header = ''.join(str(s).ljust(n)[:n] for s,n in fields)
    for width, vals in [(16,labels),(80,['none']*2),(8,['uV']*2),(8,['-1000']*2),
                        (8,['1000']*2),(8,['-32768']*2),(8,['32767']*2),
                        (80,['none']*2),(8,[str(fs)]*2),(32,['']*2)]:
        header += ''.join(str(v).ljust(width)[:width] for v in vals)
    assert len(header) == 256 + len(labels) * 256
    t = np.arange(fs*n_records)/fs
    x = np.stack([20*np.sin(2*np.pi*10*t), 200*np.sin(2*np.pi*40*t)])
    digitized = np.clip(np.rint((x+1000)*(65535/2000)-32768), -32768, 32767).astype('<i2')
    p = tmp_path/'mixed.edf'
    with p.open('wb') as f:
        f.write(header.encode('ascii'))
        for record in range(n_records):
            for ch in range(2):
                f.write(digitized[ch, record*fs:(record+1)*fs].tobytes())
    eeg = read_edf(p, modality='eeg')
    emg = read_edf(p, modality='emg')
    assert eeg.channels == ('Fz',)
    assert emg.channels == ('Chin',)
    assert eeg.data_uv.shape == (1, 2500)
    assert emg.data_uv.shape == (1, 2500)
    assert np.max(eeg.data_uv) == pytest.approx(20, abs=.08)
    # A sampled 40 Hz sine at 250 Hz need not contain its continuous-time peak.
    # Compare against the actual discrete maximum, allowing EDF quantization.
    assert np.max(emg.data_uv) == pytest.approx(np.max(x[1]), abs=.04)
