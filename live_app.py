"""Finite synthetic acquisition workbench. Run: streamlit run live_app.py."""
import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.signal import butter
import streamlit as st

from biosignal_lab.live import LiveProcessor, RingBuffer, SampleBlock, SimulatedDevice, StreamInfo, recording_bytes


st.title("BioSignal Live")
st.caption("Finite simulated acquisition · causal processing · explicit device timestamps")
st.info("Synthetic device only. Physical hardware, network acquisition and end-to-end latency have not been verified in this dashboard.")
with st.form("capture"):
    channel_count = st.slider("Live channels", 1, 16, 4)
    sfreq = st.selectbox("Live sampling frequency (Hz)", [250, 500, 1000])
    duration = st.slider("Capture duration (seconds)", 3, 30, 5)
    chunk = st.selectbox("Block samples", [25, 50, 100], index=1)
    frequency = st.slider("Synthetic tone (Hz)", 1., 80., 10.)
    filtering = st.checkbox("Causal 1–40 Hz Butterworth filter", value=True)
    drop = st.checkbox("Simulate one dropped block", value=False)
    paced_preview = st.checkbox("Animate finite capture in wall time", value=False)
    run = st.form_submit_button("Capture synthetic stream")

if run:
    info = StreamInfo(sfreq, tuple(f"CH{i+1}" for i in range(channel_count)), ("uV",) * channel_count, clock="simulated_seconds")
    device = SimulatedDevice(info, frequency=frequency)
    sos = butter(4, [1, 40], btype="bandpass", fs=sfreq, output="sos") if filtering else None
    processor = LiveProcessor(info, sos=sos, window_s=2, warmup_s=1)
    display = RingBuffer(sfreq * duration, channel_count, sfreq)
    blocks = []
    result = None
    processing = []
    started_at = time.monotonic()
    preview = st.empty()
    spectral_preview = st.empty()
    progress = st.progress(0., text="Capturing synthetic stream") if paced_preview else None
    next_preview_sample = 0
    for start in range(0, sfreq * duration, chunk):
        block = device.read(min(chunk, sfreq * duration - start))
        # The omission is deliberate and visible in sequence diagnostics.
        if drop and start == chunk:
            continue
        result = processor.process(block)
        display.append(result.block)
        blocks.append(block)
        processing.append(result.diagnostics["processing_seconds"])
        if paced_preview:
            # Pace a finite synthetic stream explicitly; never alter device timestamps.
            time.sleep(max(0., started_at + block.stop_sample / sfreq - time.monotonic()))
            progress.progress(block.stop_sample / (sfreq * duration), text="Capturing synthetic stream")
            if block.stop_sample >= next_preview_sample:
                current = display.snapshot()
                tail = min(current.data.shape[1], sfreq * 3)
                preview.line_chart(pd.DataFrame(current.data[:, -tail:].T,
                                               index=current.timestamps[-tail:], columns=info.channels),
                                   x_label="Device seconds", y_label="uV")
                if result.psd is not None:
                    spectral_preview.line_chart(pd.DataFrame(result.psd.T, index=result.frequencies,
                                                             columns=info.channels),
                                                x_label="Hz", y_label="PSD (uV²/Hz)")
                next_preview_sample = block.stop_sample + max(1, sfreq//5)
    device.close()
    preview.empty()
    spectral_preview.empty()
    if progress is not None:
        progress.empty()
    retained = display.snapshot()
    # Export exactly the contiguous retained run; never conceal a simulated gap.
    contiguous_start = next(i for i, b in enumerate(blocks) if b.start_sample == retained.start_sample)
    raw = SampleBlock(np.concatenate([b.data for b in blocks[contiguous_start:]], axis=1),
                      np.concatenate([b.timestamps for b in blocks[contiguous_start:]]), retained.start_sample)
    st.session_state["live_capture"] = (info, retained, result, raw, processing)

if "live_capture" in st.session_state:
    info, retained, result, raw, processing = st.session_state["live_capture"]
    columns = st.columns(3)
    columns[0].metric("Retained contiguous samples", retained.data.shape[1])
    columns[1].metric("Detected dropped samples", result.diagnostics["dropped_samples"])
    columns[2].metric("Processing p95 (ms)", f"{np.percentile(processing, 95)*1000:.3f}")
    st.caption("Processing duration excludes acquisition, transport and display. Simulated clock is not wall clock. Export preserves native uV units and timestamps.")
    st.line_chart(pd.DataFrame(retained.data.T, index=retained.timestamps, columns=info.channels), x_label="Device seconds", y_label="uV (causal filter if enabled)")
    if result.psd is not None:
        figure = go.Figure()
        for index, channel in enumerate(info.channels):
            figure.add_scatter(x=result.frequencies, y=10*np.log10(np.maximum(result.psd[index], 1e-15)), name=channel)
        figure.update_layout(xaxis_title="Hz", yaxis_title="PSD (dB re uV²/Hz)")
        st.plotly_chart(figure)
    else:
        st.warning("Insufficient contiguous post-warmup samples for a two-second spectrum.")
    st.json(result.diagnostics)
    st.download_button("Download contiguous raw recording (NPZ)", recording_bytes(info, raw), file_name="synthetic-live.npz", mime="application/octet-stream")
else:
    st.write("Choose acquisition settings and capture a finite deterministic stream.")
