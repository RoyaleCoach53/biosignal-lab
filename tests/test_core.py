import numpy as np
import pytest
from biosignal_lab.models import Recording, AnalysisConfig
from biosignal_lab.simulate import synthetic_recording
from biosignal_lab.pipeline import analyze
from biosignal_lab.analysis import (compute_psd, band_powers, detect_artifacts,
                                   hjorth_parameters, time_frequency_psd, pairwise_coherence,
                                   emg_descriptors)
from biosignal_lab.preprocessing import preprocess, fill_short_gaps


def test_synthetic_is_deterministic():
    a = synthetic_recording(seed=42)
    b = synthetic_recording(seed=42)
    assert np.array_equal(a.data_uv, b.data_uv)


def test_synthetic_seed_changes_data():
    assert not np.array_equal(synthetic_recording(seed=2).data_uv, synthetic_recording(seed=3).data_uv)


def test_synthetic_shape_and_duration():
    a = synthetic_recording(duration_s=12, sfreq=250, n_channels=3)
    assert a.data_uv.shape == (3, 3000)
    assert a.duration_s == 12


def test_recording_rejects_bad_shapes():
    with pytest.raises(ValueError):
        Recording(np.ones((100,)), 250, ("x",))


def test_recording_rejects_duplicate_channels():
    with pytest.raises(ValueError):
        Recording(np.ones((2, 100)), 250, ("x", "x"))


def test_recording_rejects_infinity():
    x = np.zeros((1, 100));x[0, 4] = np.inf
    with pytest.raises(ValueError):
        Recording(x, 250, ("x",))


def test_recording_rejects_invalid_sfreq():
    with pytest.raises(ValueError):
        Recording(np.zeros((1, 100)), 0, ("x",))


def test_config_rejects_bad_band():
    cfg = AnalysisConfig(highpass_hz=50, lowpass_hz=30)
    with pytest.raises(ValueError):
        cfg.validate(250, 1000)


def test_config_rejects_nyquist_violation():
    with pytest.raises(ValueError):
        AnalysisConfig(notch_hz=60).validate(100, 1000)


def test_config_rejects_window_too_long():
    with pytest.raises(ValueError):
        AnalysisConfig(window_s=20).validate(250, 250)


def test_pipeline_alpha_dominance():
    rec = synthetic_recording(duration_s=30, with_artifacts=False, n_channels=2)
    out = analyze(rec)
    for row in out.band_powers:
        assert row["alpha_uv2"] > row["beta_uv2"]
        assert row["alpha_uv2"] > row["theta_uv2"]


def test_psd_detects_ten_hz_peak():
    fs = 250; t=np.arange(2500)/fs
    f, p = compute_psd((np.sin(2*np.pi*10*t)[None, :]), fs)
    assert abs(float(f[np.argmax(p[0])])-10) < .6


def test_band_power_scales_quadratically():
    fs=250;t=np.arange(2500)/fs;x=np.sin(2*np.pi*10*t)[None,:]
    f,p=compute_psd(x,fs)
    f2,p2=compute_psd(2*x,fs)
    a=band_powers(f,p,("a",))[0]["alpha_uv2"]
    b=band_powers(f2,p2,("a",))[0]["alpha_uv2"]
    assert b/a==pytest.approx(4, rel=1e-10)


def test_notch_reduces_line_noise():
    fs=250;t=np.arange(5000)/fs
    x=(np.sin(2*np.pi*50*t)+np.sin(2*np.pi*10*t))[None,:]
    cfg=AnalysisConfig(notch_hz=50,highpass_hz=None,lowpass_hz=None)
    y,_=preprocess(x,fs,cfg)
    freq,orig=compute_psd(x,fs)
    _,filtered=compute_psd(y,fs)
    k=np.argmin(abs(freq-50))
    assert filtered[0,k]<orig[0,k]*.01


def test_no_filter_removes_dc_mean_only():
    x=np.ones((1,1000))*20
    cfg=AnalysisConfig(notch_hz=None,highpass_hz=None,lowpass_hz=None)
    y,_=preprocess(x,250,cfg)
    assert abs(np.mean(y))<1e-10


def test_missing_samples_are_interpolated():
    x=np.arange(100,dtype=float)[None,:];x[0,5:8]=np.nan
    out,w=fill_short_gaps(x,.05)
    assert out[0,6]==pytest.approx(6)
    assert len(w)==1


def test_excessive_missing_rejected():
    x=np.arange(100,dtype=float)[None,:];x[0,:20]=np.nan
    with pytest.raises(ValueError):
        fill_short_gaps(x,.05)


def test_flatline_artifact():
    out=detect_artifacts(np.zeros((1,1000)),250,("Fp1",),window_s=2,
                         threshold_mad=8,flatline_tolerance_uv=.15)
    assert len(out)==2
    assert all(a["reason"]=="flatline_candidate" for a in out)


def test_emg_omits_eeg_bands():
    rec=synthetic_recording(modality="emg",sfreq=500,n_channels=2)
    result=analyze(rec)
    assert result.band_powers==[]
    assert any("EMG" in w for w in result.warnings)


def test_modality_mismatch_rejected():
    rec=synthetic_recording(modality="eeg")
    with pytest.raises(ValueError):
        analyze(rec,AnalysisConfig(modality="emg"))


def test_summary_includes_processing_config():
    rec=synthetic_recording(duration_s=5,n_channels=1)
    res=analyze(rec)
    assert "highpass_hz" in res.summary()["config"]


def test_hjorth_constant_signal_is_zero():
    metrics = hjorth_parameters(np.ones(400), 250)
    assert all(v == 0.0 for v in metrics.values())


def test_hjorth_activity_is_variance():
    signal = np.array([0., 1., 2., 3., 4., 5.])
    assert hjorth_parameters(signal, 250)["hjorth_activity_uv2"] == pytest.approx(np.var(signal))


def test_hjorth_requires_positive_sfreq():
    with pytest.raises(ValueError):
        hjorth_parameters(np.arange(100), 0)


def test_time_frequency_detects_alpha_peak():
    fs = 250
    t = np.arange(fs*10)/fs
    f, seconds, spec = time_frequency_psd(np.sin(2*np.pi*10*t), fs)
    assert abs(float(f[np.argmax(spec.mean(axis=1))])-10) < .6
    assert len(seconds) > 1


def test_time_frequency_rejects_invalid_data():
    with pytest.raises(ValueError):
        time_frequency_psd(np.ones(5), 250)


def test_coherence_identical_channels_close_to_one():
    rng = np.random.default_rng(1)
    x = rng.normal(size=2500)
    f, coh = pairwise_coherence(x,x,250)
    assert np.min(coh) > .999


def test_coherence_zero_to_one():
    rng = np.random.default_rng(3)
    f, coh = pairwise_coherence(rng.normal(size=2500),rng.normal(size=2500),250)
    assert np.all((coh >= 0) & (coh <= 1))


def test_coherence_rejects_mismatched_channels():
    with pytest.raises(ValueError):
        pairwise_coherence(np.ones(200), np.ones(100), 250)


def test_emg_descriptors_median_freq():
    fs=500
    t=np.arange(5000)/fs
    x=np.sin(2*np.pi*70*t)
    metrics=emg_descriptors(x,fs)
    assert abs(metrics["emg_median_frequency_hz"]-70) < 2
    assert metrics["emg_rms_uv"] == pytest.approx(1/np.sqrt(2),rel=.01)


def test_emg_descriptors_rejects_invalid_input():
    with pytest.raises(ValueError):
        emg_descriptors(np.array([1., 2.]), 250)


def test_eeg_quality_includes_hjorth_metrics():
    result=analyze(synthetic_recording(duration_s=6,n_channels=1))
    assert "hjorth_complexity" in result.channel_metrics[0]


def test_emg_quality_includes_emg_metrics():
    result=analyze(synthetic_recording(duration_s=6,sfreq=500,modality="emg",n_channels=1))
    assert "emg_median_frequency_hz" in result.channel_metrics[0]
