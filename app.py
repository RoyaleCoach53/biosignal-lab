"""Streamlit entry point. All processing runs where the app is hosted.

Run locally for privacy: streamlit run app.py. Do not deploy to a third-party
server with personal or clinical recordings without an appropriate privacy review.
"""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from biosignal_lab.models import AnalysisConfig
from biosignal_lab.pipeline import default_config
from biosignal_lab.io import read_csv, read_edf
from biosignal_lab.simulate import synthetic_recording
from biosignal_lab.pipeline import analyze
from biosignal_lab.report import html_report, json_report
from biosignal_lab.analysis import time_frequency_psd, pairwise_coherence

st.set_page_config(page_title="BioSignal Lab | EEG & EMG", page_icon="🧠",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
.block-container {padding-top: 2rem;} h1,h2,h3 {letter-spacing:-0.025em;}
[data-testid='stMetricValue'] {font-size:2rem;}
</style>""", unsafe_allow_html=True)

st.title("🧠 BioSignal Lab")
st.caption("Open-source EEG/EMG analysis · Local-first · Reproducible · Research & education only")
st.warning("Not a medical device. No diagnosis, seizure detection or clinical decisions. Do not upload personal clinical recordings to a hosted copy.")

with st.sidebar:
    st.header("Recording")
    source = st.radio("Data source", ["Synthetic demo", "Upload CSV / EDF"])
    modality = st.selectbox("Signal type", ["eeg", "emg"], format_func=str.upper)
    if source == "Synthetic demo":
        sfreq = st.selectbox("Sampling frequency (Hz)", [250, 500, 1000], index=0)
        duration = st.slider("Duration (seconds)", 10, 120, 30, 5)
        n_channels = st.slider("Channels", 1, 16, 8)
        seed = st.number_input("Random seed", min_value=0, max_value=999999, value=42)
        demo_artifacts = st.toggle("Include simulated artifact", value=True)
        recording = synthetic_recording(sfreq=sfreq, duration_s=duration, n_channels=n_channels,
                                        modality=modality, seed=int(seed), with_artifacts=demo_artifacts)
    else:
        uploaded = st.file_uploader("Choose a local recording", type=["csv", "edf"],
                                    help="Prefer anonymized recordings. CSV channels must be numeric.")
        if not uploaded:
            st.info("Choose a CSV or EDF file to start, or use the synthetic demo.")
            st.stop()
        st.caption("File is processed by this app's Python process; use local mode for sensitive data.")
        if uploaded.name.lower().endswith(".csv"):
            sfreq = st.number_input("Sampling frequency (Hz) — required", 10.0, 10000.0, 250.0, 10.0)
            unit = st.selectbox("Amplitude unit in CSV", ["uv", "mv", "v"], index=0)
            time_column = st.text_input("Time column to exclude (optional)", value="")
        with tempfile.TemporaryDirectory() as tmp:
            suffix = Path(uploaded.name).suffix.lower()
            dest = Path(tmp) / ("input" + suffix)
            dest.write_bytes(uploaded.getvalue())
            try:
                if suffix == ".csv":
                    recording = read_csv(dest, sfreq=sfreq, unit=unit, modality=modality,
                                         time_column=time_column.strip() or None)
                else:
                    recording = read_edf(dest, modality=modality)
            except (ValueError, RuntimeError, ImportError, OSError) as exc:
                st.error(f"Could not load recording: {exc}")
                st.stop()
    if recording.duration_s < .5:
        st.error("Recordings shorter than 0.5 seconds are not supported in the dashboard.")
        st.stop()
    if recording.sfreq < 10:
        st.error("The dashboard requires a sampling rate of at least 10 Hz. Use the Python API for lower-rate research signals.")
        st.stop()
    st.divider()
    st.header("Preprocessing")
    nyquist = recording.sfreq / 2
    defaults = default_config(modality, recording.sfreq)
    default_hp = defaults.highpass_hz
    default_lp = defaults.lowpass_hz
    use_hp = st.toggle("High-pass filter", value=(default_hp is not None))
    hp = st.number_input("High-pass (Hz)", min_value=.05, max_value=float(nyquist*.95),
                         value=float(default_hp or .1), step=.05, disabled=not use_hp)
    use_lp = st.toggle("Low-pass filter", value=(default_lp is not None))
    suggested_lp = default_lp if default_lp is not None else min(80., nyquist*.8)
    lp = st.number_input("Low-pass (Hz)", min_value=.2, max_value=float(nyquist*.99),
                         value=float(suggested_lp), step=1., disabled=not use_lp)
    notch_opts = ["None"] + (["50 Hz"] if nyquist > 50 else []) + (["60 Hz"] if nyquist > 60 else [])
    notch_label = st.selectbox("Power-line notch", notch_opts,
                               index=(notch_opts.index("50 Hz") if "50 Hz" in notch_opts else 0))
    notch_hz = None if notch_label == "None" else float(notch_label.split()[0])
    max_window = min(10.0, float(recording.duration_s))
    if max_window > .5:
        window = st.slider("Spectral window (s)", .5, max_window,
                           min(4.0 if modality == "eeg" else 2.0, max_window), .5)
        artifact_window = st.slider("Artifact review window (s)", .5, max_window,
                                    min(1.0, max_window), .5)
    else:
        window = artifact_window = max_window
        st.caption("The full 0.5-second recording is used for both windows.")
    threshold = st.slider("Artifact threshold (robust MAD multiplier)", 3., 20., 8., 1.)

try:
    config = AnalysisConfig(modality=modality, highpass_hz=float(hp) if use_hp else None,
                            lowpass_hz=float(lp) if use_lp else None, notch_hz=notch_hz,
                            window_s=float(window), artifact_window_s=float(artifact_window),
                            artifact_threshold_mad=float(threshold))
    result = analyze(recording, config)
except ValueError as exc:
    st.error(f"Analysis settings are invalid: {exc}")
    st.stop()

cols = st.columns(4)
cols[0].metric("Channels", len(recording.channels))
cols[1].metric("Sample rate", f"{recording.sfreq:g} Hz")
cols[2].metric("Duration", f"{recording.duration_s:.1f} s")
cols[3].metric("Artifact candidates", len(result.artifact_intervals))
for warning in result.warnings:
    st.info(warning)

signals, spectrum, tf_tab, channel_qc, artifacts, export = st.tabs(
    ["📈 Signal Explorer", "🌊 Spectrum", "🔥 Time-Frequency",
     "🛡️ Channel Quality", "🚩 Artifact Review", "📥 Export"])

with signals:
    channel = st.selectbox("Channel", list(recording.channels))
    idx = recording.channels.index(channel)
    max_view = min(float(recording.duration_s), 30.)
    max_start = max(0., float(recording.duration_s) - max_view)
    if max_start > 0:
        start = st.slider("View from (s)", 0., max_start, 0., step=.5)
    else:
        start = 0.
        st.caption("Showing the complete recording.")
    stop = min(float(recording.duration_s), start + max_view)
    i0, i1 = int(start*recording.sfreq), int(stop*recording.sfreq)
    step = max(1, (i1-i0)//3000)
    ts = np.arange(i0, i1, step)/recording.sfreq
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ts, y=recording.data_uv[idx, i0:i1:step],
                             name="Raw", mode="lines", line=dict(color="#94a3b8", width=1)))
    fig.add_trace(go.Scatter(x=ts, y=result.processed_uv[idx, i0:i1:step],
                             name="Filtered", mode="lines", line=dict(color="#8b5cf6", width=1.4)))
    for interval in result.artifact_intervals:
        if interval["channel"] == channel and interval["end_s"] >= start and interval["start_s"] <= stop:
            fig.add_vrect(x0=interval["start_s"], x1=interval["end_s"],
                          fillcolor="orange", opacity=.13, line_width=0)
    fig.update_layout(xaxis_title="Time (seconds)", yaxis_title="Amplitude (µV)",
                      height=470, legend=dict(orientation="h"), margin=dict(l=10,r=10,t=20,b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Orange shading indicates heuristic review candidates, not diagnosed artifacts.")

with spectrum:
    channel_spec = st.selectbox("Channel for PSD", list(recording.channels), key="spec")
    idx = recording.channels.index(channel_spec)
    f = result.frequencies_hz
    p = result.psd_uv2_per_hz[idx]
    plot = go.Figure()
    plot.add_trace(go.Scatter(x=f, y=10*np.log10(np.maximum(p, 1e-12)),
                              mode="lines", name="PSD", fill="tozeroy", line_color="#7c3aed"))
    plot.update_layout(xaxis_title="Frequency (Hz)", yaxis_title="Power (dB re µV²/Hz)", height=450,
                       margin=dict(l=10,r=10,t=20,b=10))
    plot.update_xaxes(range=[0, min(100, recording.sfreq/2)])
    st.plotly_chart(plot, use_container_width=True)
    if result.band_powers:
        table = pd.DataFrame(result.band_powers).set_index("channel")
        band_names = ["delta", "theta", "alpha", "beta", "gamma"]
        st.subheader("EEG frequency band power")
        cols = st.columns(5)
        for col, band in zip(cols, band_names):
            value = table.loc[channel_spec, band+'_uv2']
            col.metric(band.title(), "Unavailable" if pd.isna(value) else f"{value:.2f} µV²")
        st.caption("Unavailable bands are not shown as zero. Relative powers are fractions of 0.5–min(45 Hz, Nyquist), and only complete bands have numerical values.")
        st.dataframe(pd.DataFrame(result.band_powers), use_container_width=True)
    else:
        st.info("EEG band powers intentionally unavailable for EMG.")

with tf_tab:
    channel_tf = st.selectbox("Channel for spectrogram", list(recording.channels), key="tf")
    idx = recording.channels.index(channel_tf)
    freqs_tf, times_tf, power_tf = time_frequency_psd(
        result.processed_uv[idx], recording.sfreq, config.window_s)
    mask = freqs_tf <= min(100, recording.sfreq/2)
    figure = go.Figure(data=go.Heatmap(
        x=times_tf, y=freqs_tf[mask],
        z=10*np.log10(np.maximum(power_tf[mask], 1e-12)),
        colorscale="Viridis", colorbar=dict(title="dB re µV²/Hz")))
    figure.update_layout(xaxis_title="Time (s)", yaxis_title="Frequency (Hz)", height=430)
    st.plotly_chart(figure, use_container_width=True)
    st.caption("Descriptive short-time PSD. Spectral patterns do not establish a medical diagnosis.")
    if len(recording.channels) >= 2:
        st.subheader("Pairwise coherence — research only")
        ch_a = st.selectbox("First channel", list(recording.channels), index=0, key="ca")
        ch_b = st.selectbox("Second channel", list(recording.channels), index=1, key="cb")
        if ch_a != ch_b:
            try:
                f_coh, coh = pairwise_coherence(
                    result.processed_uv[recording.channels.index(ch_a)],
                    result.processed_uv[recording.channels.index(ch_b)],
                    recording.sfreq, config.window_s)
            except ValueError as exc:
                st.info(f"Coherence unavailable: {exc}")
            else:
                figure_c = go.Figure(data=go.Scatter(x=f_coh, y=coh, mode="lines"))
                figure_c.update_layout(xaxis_title="Frequency (Hz)",
                                       yaxis_title="Magnitude-squared coherence", height=280)
                figure_c.update_yaxes(range=[0, 1])
                figure_c.update_xaxes(range=[0, min(100, recording.sfreq/2)])
                st.plotly_chart(figure_c, use_container_width=True)
        st.caption("Coherence is not proof of neural connectivity; common references, volume conduction and artifacts can inflate it.")

with channel_qc:
    st.dataframe(pd.DataFrame(result.channel_metrics), use_container_width=True, hide_index=True)
    st.caption("Metrics describe the processed signal. They do not provide clinical signal suitability approval.")

with artifacts:
    st.write("Candidates are generated using robust amplitude excursions and flatline windows on **unfiltered** data.")
    if result.artifact_intervals:
        st.dataframe(pd.DataFrame(result.artifact_intervals), use_container_width=True, hide_index=True)
    else:
        st.success("No artifact candidates under these thresholds (not evidence of clean clinical data).")

with export:
    st.markdown("All downloaded reports contain channel statistics and processing settings. The HTML and JSON reports do **not** contain sample-by-sample recordings.")
    a, b, c = st.columns(3)
    a.download_button("⬇️ JSON report", json_report(result), file_name="biosignal_report.json", mime="application/json")
    b.download_button("⬇️ HTML report", html_report(result), file_name="biosignal_report.html", mime="text/html")
    c.download_button("⬇️ Channel metrics CSV", pd.DataFrame(result.channel_metrics).to_csv(index=False),
                      file_name="channel_quality.csv", mime="text/csv")
    if result.band_powers:
        st.download_button("⬇️ EEG bands CSV", pd.DataFrame(result.band_powers).to_csv(index=False),
                           file_name="band_powers.csv", mime="text/csv")
    if result.artifact_intervals:
        st.download_button("⬇️ Artifact candidates CSV", pd.DataFrame(result.artifact_intervals).to_csv(index=False),
                           file_name="artifact_candidates.csv", mime="text/csv")
    st.download_button("⬇️ Processing configuration", json.dumps(config.__dict__, indent=2),
                       file_name="processing_config.json", mime="application/json")

st.caption("BioSignal Lab v0.2.0 • MIT license • Research / education only • See docs/SCIENTIFIC_AUDIT.md")
