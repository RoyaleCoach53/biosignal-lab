"""Interactive unit-aware processing, separate from the preserved EEG/EMG pipeline."""
import json
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from biosignal_lab.engine import (
    Signal, FilterSpec, filter_signal, resample_signal, normalize_signal,
    welch_psd, spectral_entropy, save_signal,
)

st.set_page_config(page_title="BioSignal Engine", layout="wide")
st.title("Scientific Engine")
st.caption("Explicit units, filter direction and provenance. Research and education only.")
st.info("Calibration tones test mathematical behavior; modality labels do not make them physiological simulations.")
with st.sidebar:
    source = st.radio("Engine input", ["Calibration tones", "Numeric CSV"])
    modality = st.selectbox("Measurement modality", ["eeg", "emg", "ecg", "eog", "ppg", "eda", "other"])
    unit = st.selectbox("Physical unit", ["uV", "mV", "V", "a.u.", "uS", "S"])
    sfreq = st.number_input("Input sampling frequency (Hz)", 10., 5000., 250., step=10.)
    reference = st.text_input("Reference or measurement description", "Unspecified")

try:
    if source == "Calibration tones":
        t = np.arange(round(sfreq * 10)) / sfreq
        data = np.vstack([np.sin(2*np.pi*2*t) + .5*np.sin(2*np.pi*min(30., sfreq*.4)*t),
                          np.sin(2*np.pi*2*t + .4)])
        channels = ("Calibration A", "Calibration B")
    else:
        uploaded = st.file_uploader("CSV with numeric channels", type=["csv"])
        if uploaded is None:
            st.stop()
        if uploaded.size > 10_000_000:
            raise ValueError("CSV import is limited to ten megabytes")
        frame = pd.read_csv(uploaded, nrows=1_000_001)
        time_column = st.selectbox("Timestamp column to exclude", ["None", *frame.columns])
        if time_column != "None":
            times = pd.to_numeric(frame[time_column], errors="raise").to_numpy()
            if not np.all(np.isfinite(times)) or len(times) < 2 or not np.allclose(np.diff(times), 1/sfreq, rtol=.01, atol=1e-8):
                raise ValueError("Timestamp spacing must agree with the explicit sampling frequency")
            frame = frame.drop(columns=time_column)
        if len(frame) > 1_000_000 or not 1 <= len(frame.columns) <= 32 or frame.size > 4_000_000:
            raise ValueError("CSV exceeds channel/sample limits")
        data, channels = frame.to_numpy(dtype=float).T, tuple(map(str, frame.columns))
    raw = Signal(data, sfreq, channels, modality, unit, reference,
                 metadata={"input_kind": "synthetic_calibration" if source == "Calibration tones" else "uploaded_numeric_csv"})
    with st.sidebar:
        family = st.selectbox("Filter family", ["butter", "cheby1", "cheby2", "bessel", "ellip", "fir"])
        kind = st.selectbox("Filter response", ["bandpass", "lowpass", "highpass", "bandstop", "notch"])
        phase = st.selectbox("Filter direction", ["zero", "causal"])
        low = st.number_input("Lower or single cutoff (Hz)", .01, float(sfreq/2-.01), min(1., sfreq/4))
        high = st.number_input("Upper cutoff (Hz)", .02, float(sfreq/2-.001), min(40., sfreq*.4))
        order = st.number_input("FIR taps (odd)" if family == "fir" else "IIR order", 3 if family == "fir" else 1,
                                301 if family == "fir" else 12, 31 if family == "fir" else 4)
        output_rate = st.number_input("Output sampling frequency (Hz)", 5., 5000., float(sfreq), step=5.)
        normalize = st.checkbox("Normalize to dimensionless z-scores")
    cutoff = (low, high) if kind in {"bandpass", "bandstop"} else low
    processed = filter_signal(raw, FilterSpec(family=family, kind=kind, cutoff=cutoff, order=int(order), phase=phase))
    if output_rate != sfreq:
        processed = resample_signal(processed, output_rate)
    if normalize:
        processed = normalize_signal(processed)
    frequency, power = welch_psd(processed, window_s=min(2., processed.duration_s))
    st.metric("Channels", len(processed.channels))
    st.metric("Output sample rate", f"{processed.sfreq:g} Hz")
    st.caption(f"Output unit: {processed.unit}; PSD density: {processed.unit}²/Hz. Zero phase is acausal; causal filters start from zero state.")
    channel = st.selectbox("Engine channel", list(processed.channels))
    index = processed.channels.index(channel)
    chart = go.Figure()
    if not normalize:
        step = max(1, raw.data.shape[1]//3000)
        chart.add_scatter(x=np.arange(raw.data.shape[1])[::step]/raw.sfreq,
                          y=raw.data[index, ::step], name="Input")
    step = max(1, processed.data.shape[1]//3000)
    chart.add_scatter(x=np.arange(processed.data.shape[1])[::step]/processed.sfreq,
                      y=processed.data[index, ::step], name="Processed")
    chart.update_layout(xaxis_title="Seconds", yaxis_title=processed.unit)
    st.plotly_chart(chart)
    psd = go.Figure(go.Scatter(x=frequency, y=power[index], name="Welch PSD"))
    psd.update_layout(xaxis_title="Hz", yaxis_title=f"{processed.unit}²/Hz")
    st.plotly_chart(psd)
    entropy = spectral_entropy(power)
    st.write("Normalized spectral entropy by channel", np.asarray(entropy).tolist())
    manifest = {"modality": processed.modality, "unit": processed.unit,
                "sfreq": processed.sfreq, "reference": processed.reference,
                "channels": processed.channels, "history": processed.history,
                "metadata": dict(processed.metadata)}
    with st.expander("Processing provenance"):
        st.json(manifest)
    st.download_button("Export processing JSON", json.dumps(manifest, indent=2, allow_nan=False),
                       file_name="processing.json", mime="application/json")
    with tempfile.TemporaryDirectory(prefix="biosignal-export-") as folder:
        destination = Path(folder) / "signal.npz"
        save_signal(processed, destination)
        st.download_button("Export processed signal with metadata", destination.read_bytes(),
                           file_name="processed-signal.npz", mime="application/octet-stream")
except (ValueError, OSError, TypeError) as error:
    st.error(f"Processing failed: {error}")
