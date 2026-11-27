import socket
import struct
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import numpy as np
import pytest
from scipy.signal import butter, sosfilt

from biosignal_lab.live import (LiveProcessor, PlaybackDevice, RingBuffer, SampleBlock,
                               SimulatedDevice, StreamInfo, TCPDevice, encode_frame,
                               load_recording, save_recording, ClockAlignment)


def info(channels=2):
    return StreamInfo(250, tuple(f"CH{i}" for i in range(channels)), ("uV",) * channels)


def block(start=0, count=10):
    return SampleBlock(np.tile(np.arange(start, start+count), (2, 1)),
                       np.arange(start, start+count)/250, start)


def test_simulated_source_is_chunk_invariant_and_closed_state_explicit():
    whole = SimulatedDevice(info()).read(73)
    source = SimulatedDevice(info())
    parts = [source.read(n) for n in (1, 7, 25, 40)]
    np.testing.assert_array_equal(whole.data, np.concatenate([b.data for b in parts], axis=1))
    np.testing.assert_array_equal(whole.timestamps, np.concatenate([b.timestamps for b in parts]))
    source.close()
    with pytest.raises(RuntimeError, match="closed"):
        source.read(10)
    reconnect = SimulatedDevice(info()).read(10)
    assert reconnect.start_sample == 0


def test_sample_block_owns_readonly_copy_and_rejects_ambiguous_data():
    data = np.zeros((2, 4))
    sample = SampleBlock(data, np.arange(4), 0)
    data[:] = 7
    assert np.max(sample.data) == 0
    assert not sample.data.flags.writeable
    with pytest.raises(ValueError):
        SampleBlock(np.ones((2, 4)), [0, 1, 1, 2], 0)
    with pytest.raises(ValueError):
        SampleBlock(np.full((2, 4), np.nan), np.arange(4), 0)
    with pytest.raises(ValueError):
        SampleBlock(np.zeros((2, 4)), np.arange(4), 1.5)


def test_ring_wrap_gap_overflow_and_out_of_order_are_distinct():
    ring = RingBuffer(7, 2, 250)
    ring.append(block(0, 5))
    ring.append(block(5, 5))
    np.testing.assert_array_equal(ring.snapshot().data[0], np.arange(3, 10))
    assert ring.diagnostics()["overwritten_samples"] == 3
    assert ring.append(block(15, 3))
    assert ring.diagnostics()["dropped_samples"] == 5
    assert ring.snapshot().start_sample == 15
    with pytest.raises(ValueError, match="out-of-order"):
        ring.append(block(16, 3))
    assert ring.snapshot().stop_sample == 18
    ring.append(block(18, 15))
    np.testing.assert_array_equal(ring.snapshot().data[0], np.arange(26, 33))


def test_ring_rejects_wrong_clock_rate_and_resets_on_timestamp_jump():
    ring = RingBuffer(20, 2, 250)
    ring.append(block())
    with pytest.raises(ValueError, match="sampling frequency"):
        ring.append(SampleBlock(np.ones((2, 3)), [1, 2, 3], 10))
    shifted = block(10, 5)
    assert ring.append(SampleBlock(shifted.data, shifted.timestamps + 1, 10))
    assert ring.diagnostics()["discontinuities"] == 1
    assert ring.snapshot().data.shape == (2, 5)


def test_ring_concurrent_snapshot_never_exposes_torn_blocks():
    ring = RingBuffer(101, 2, 250)
    done = Event()

    def writer():
        try:
            for start in range(0, 4000, 10):
                ring.append(block(start, 10))
        finally:
            done.set()

    with ThreadPoolExecutor(2) as pool:
        future = pool.submit(writer)
        while not done.is_set():
            sample = ring.snapshot()
            if sample is not None:
                np.testing.assert_array_equal(sample.data[0], np.arange(sample.start_sample, sample.stop_sample))
                np.testing.assert_array_equal(sample.data[0], sample.data[1])
        future.result()
    assert ring.snapshot().stop_sample == 4000


def test_causal_filter_matches_continuous_scipy_and_reset_prevents_gap_bridging():
    source = SimulatedDevice(info())
    full = source.read(1000)
    sos = butter(4, [1, 40], btype="bandpass", fs=250, output="sos")
    expected = sosfilt(sos, full.data, axis=1)
    processor = LiveProcessor(info(), sos, window_s=1, warmup_s=.5)
    outputs = []
    for begin in range(0, 1000, 100):
        result = processor.process(SampleBlock(full.data[:, begin:begin+100], full.timestamps[begin:begin+100], begin))
        outputs.append(result.block.data)
    np.testing.assert_allclose(np.concatenate(outputs, axis=1), expected, atol=1e-12)
    assert result.psd.shape == (2, 126)
    after_gap = source.read(100)
    gap = SampleBlock(after_gap.data, after_gap.timestamps + .4, 1100)
    reset = processor.process(gap)
    np.testing.assert_allclose(reset.block.data, sosfilt(sos, gap.data, axis=1))
    assert reset.diagnostics["filter_reset"]
    assert reset.diagnostics["dropped_samples"] == 100
    assert reset.psd is None


def test_live_psd_peak_and_power_have_correct_physical_units():
    t = np.arange(1000)/250
    data = np.tile(10*np.sin(2*np.pi*10*t), (2, 1))
    result = LiveProcessor(info(), window_s=4).process(SampleBlock(data, t, 0))
    assert result.frequencies[np.argmax(result.psd[0])] == pytest.approx(10)
    assert np.trapezoid(result.psd[0], result.frequencies) == pytest.approx(50, rel=.001)
    assert not result.diagnostics["filter_reset"]


def test_recording_roundtrip_playback_and_no_overwrite(tmp_path):
    path = tmp_path / "recording.npz"
    sample = block(10, 20)
    markers = [{"sample": 15, "label": "stimulus"}]
    save_recording(path, info(), sample, markers)
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        save_recording(path, info(), block())
    assert path.read_bytes() == original
    metadata, loaded, events = load_recording(path)
    assert metadata == info() and events == markers
    np.testing.assert_array_equal(loaded.data, sample.data)
    playback = PlaybackDevice(path)
    assert playback.read(7).start_sample == 10
    assert playback.read(100).data.shape == (2, 13)
    with pytest.raises(EOFError):
        playback.read(1)


def test_recording_rejects_pickle_extra_members_and_limits(tmp_path):
    path = tmp_path / "bad.npz"
    np.savez(path, data=np.array([object()], dtype=object), timestamps=np.arange(3), metadata=np.array("{}"))
    with pytest.raises(ValueError):
        load_recording(path)
    np.savez(path, data=np.ones((2, 10)), timestamps=np.arange(10), metadata=np.array("{}"), surprise=np.ones(10))
    with pytest.raises(ValueError, match="archive"):
        load_recording(path)
    good = tmp_path / "good.npz"
    save_recording(good, info(), block())
    with pytest.raises(ValueError, match="size"):
        load_recording(good, max_values=2)
    with pytest.raises(ValueError, match="Marker"):
        save_recording(tmp_path / "marker.npz", info(), block(), [{"sample": 999, "label": "outside"}])


def test_tcp_loopback_partial_frames_preserve_sample_metadata():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    client = socket.create_connection(server.getsockname())
    peer, _ = server.accept()
    server.close()
    device = TCPDevice(peer, info())
    payload = encode_frame(block())
    with ThreadPoolExecutor(1) as pool:
        def send():
            for offset in range(0, len(payload), 7):
                client.sendall(payload[offset:offset+7])
        sender = pool.submit(send)
        sample = device.read(10)
        sender.result()
    np.testing.assert_array_equal(sample.data, block().data)
    assert sample.start_sample == 0
    client.close()
    with pytest.raises(EOFError):
        device.read()
    with pytest.raises(RuntimeError, match="closed"):
        device.read()


def test_tcp_oversized_frame_disconnects_before_payload_allocation():
    left, right = socket.socketpair()
    device = TCPDevice(right, info(), max_bytes=1024)
    left.sendall(struct.pack("!I", 1025))
    with pytest.raises(ValueError, match="byte limit"):
        device.read()
    with pytest.raises(RuntimeError, match="closed"):
        device.read()
    left.close()


def test_clock_calibration_recovers_drift_and_refuses_silent_extrapolation():
    device = np.linspace(1000, 1060, 10)
    host = device * 1.0001 + 500
    alignment = ClockAlignment.fit(device, host)
    assert alignment.scale == pytest.approx(1.0001)
    assert alignment.residual_rms_s < 1e-10
    np.testing.assert_allclose(alignment.transform(device), host, atol=1e-10)
    with pytest.raises(ValueError, match="calibration interval"):
        alignment.transform([1061])
    assert alignment.transform([1061], allow_extrapolation=True)[0] == pytest.approx(1061*1.0001+500)
    with pytest.raises(ValueError, match="paired"):
        ClockAlignment.fit([1, 1, 1], [2, 3, 4])


def test_live_dashboard_capture_has_real_signal_psd_and_gap_detection():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    dashboard = AppTest.from_file(str(Path(__file__).resolve().parents[2] / "live_app.py"), default_timeout=30).run()
    # tests/live lives two parents below repository root.
    assert not dashboard.exception
    dashboard.button[0].click().run()
    assert not dashboard.exception
    assert any(metric.label == "Retained contiguous samples" for metric in dashboard.metric)
    assert len(dashboard.get("plotly_chart")) == 1
    next(x for x in dashboard.checkbox if x.label == "Simulate one dropped block").set_value(True)
    dashboard.button[0].click().run()
    assert not dashboard.exception
    lost = next(metric for metric in dashboard.metric if metric.label == "Detected dropped samples")
    assert lost.value == "50"
