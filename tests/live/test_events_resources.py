from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
import platform

import numpy as np
import pytest

from biosignal_lab.live import (AcquisitionSession, EventMarker, LiveProcessor,
                               PlaybackDevice, RingBuffer, SampleBlock, SimulatedDevice,
                               StreamInfo, load_recording, process_memory_usage, save_recording)


def info():
    return StreamInfo(250, ("C3", "C4"), ("uV", "uV"), clock="explicit_device_seconds")


def block(start):
    return SampleBlock(np.tile(np.arange(start, start+4), (2, 1)),
                       10000 + np.arange(start, start+4)/250, start)


def test_sample_clock_markers_preserve_gap_eviction_checkpoint_and_replay(tmp_path):
    ready, release = Event(), Event()

    class GappedDevice:
        info = info()

        def __init__(self):
            self.calls = 0

        def read(self, n):
            self.calls += 1
            if self.calls == 1:
                return block(0)
            if self.calls == 2:
                ready.set()  # Previous block has been committed by the worker.
                if not release.wait(3):
                    raise TimeoutError("test synchronization")
                return block(8)
            raise EOFError("finished")

        def close(self):
            pass

    session = AcquisitionSession(GappedDevice(), LiveProcessor(info()), max_samples=12,
                                 block_samples=4, buffer_seconds=.016).start()
    try:
        assert ready.wait(2)
        before_gap = session.add_marker("before gap", sample=2)
        assert before_gap.timestamp == block(0).timestamps[2]
        assert before_gap.clock == info().clock and before_gap.source == "explicit_sample"
    finally:
        release.set()
    assert session.wait(3)["state"] == "disconnected"
    assert session.status()["buffer"]["dropped_samples"] == 4
    with pytest.raises(ValueError, match="absent, dropped"):
        session.add_marker("missing source sample", sample=5)
    with pytest.raises(ValueError, match="absent, dropped"):
        session.add_marker("evicted source sample", sample=2)
    latest = session.add_marker("latest received")
    assert latest.sample == 11 and latest.timestamp == block(8).timestamps[-1]
    assert latest.source == "latest_received_sample"
    checkpoint = tmp_path / "capture.npz"
    report = session.checkpoint(checkpoint)
    assert report["markers_saved"] == 1 and report["markers_outside_retained_window"] == 1
    original = checkpoint.read_bytes()
    with pytest.raises(FileExistsError):
        session.checkpoint(checkpoint)
    assert checkpoint.read_bytes() == original
    _, raw, stored = load_recording(checkpoint)
    np.testing.assert_array_equal(raw.data, block(8).data)
    assert stored == [latest.to_dict()]
    replay = PlaybackDevice(checkpoint)
    recovered = AcquisitionSession(replay, LiveProcessor(replay.info), max_samples=4,
                                   block_samples=2, buffer_seconds=1).start()
    assert recovered.wait(3)["state"] == "completed"
    assert recovered.markers() == (latest,)
    np.testing.assert_array_equal(recovered.raw_snapshot().timestamps, block(8).timestamps)


def test_cancelled_capture_keeps_only_actual_committed_sample_events(tmp_path):
    ready, release = Event(), Event()

    class BlockingDevice:
        info = info()

        def __init__(self):
            self.calls = 0

        def read(self, n):
            self.calls += 1
            if self.calls == 1:
                return block(0)
            ready.set()
            release.wait(3)
            return block(4)

        def close(self):
            pass

    session = AcquisitionSession(BlockingDevice(), LiveProcessor(info()), max_samples=8,
                                 block_samples=4).start()
    try:
        assert ready.wait(2)
        marker = session.add_marker("committed pre-cancel sample", sample=3)
        with pytest.raises(TimeoutError, match="remains active"):
            session.stop(.01)
        assert session.status()["state"] == "running"
    finally:
        release.set()
    assert session.wait(2)["state"] == "stopped"
    assert session.raw_snapshot().stop_sample == 4
    assert session.markers() == (marker,)
    with pytest.raises(ValueError, match="absent, dropped"):
        session.add_marker("uncommitted post-cancel sample", sample=4)
    report = session.checkpoint(tmp_path / "cancelled.npz")
    assert report["markers_saved"] == 1 and report["stop_sample"] == 4


def test_concurrent_markers_are_bounded_and_legacy_archives_keep_sample_provenance(tmp_path):
    session = AcquisitionSession(SimulatedDevice(info()), LiveProcessor(info()), max_samples=50,
                                 max_markers=16).start()
    session.wait(3)
    with ThreadPoolExecutor(4) as pool:
        markers = list(pool.map(lambda index: session.add_marker(f"event {index}", sample=index), range(16)))
    assert len(session.markers()) == 16
    assert len({m.sample for m in markers}) == 16
    for marker in markers:
        assert marker.timestamp == session.raw_snapshot().timestamps[marker.sample]
    with pytest.raises(ValueError, match="limit"):
        session.add_marker("too many", sample=20)
    legacy = tmp_path / "legacy.npz"
    save_recording(legacy, info(), block(8), [{"sample": 9, "label": "legacy"}])
    playback = PlaybackDevice(legacy)
    playback.read(2)
    assert playback.last_markers[0].source == "legacy_sample_reference"
    assert playback.last_markers[0].timestamp == block(8).timestamps[1]
    playback.read(2)
    assert playback.last_markers == ()
    playback.close()


def test_marker_timestamp_clock_and_label_validation_prevents_silent_retiming(tmp_path):
    correct = EventMarker.from_block(info(), block(8), "event", sample=9)
    changed_clock = dict(correct.to_dict(), clock="host_monotonic")
    changed_time = dict(correct.to_dict(), timestamp=correct.timestamp + .001)
    for marker in (changed_clock, changed_time):
        with pytest.raises(ValueError, match="timestamp/clock"):
            save_recording(tmp_path / "bad.npz", info(), block(8), [marker])
    for label in ("", "x"*257):
        with pytest.raises(ValueError, match="label"):
            EventMarker.from_block(info(), block(8), label)
    with pytest.raises(ValueError, match="timestamp"):
        EventMarker(9, "10000.004", info().clock, "string timestamp")
    empty = AcquisitionSession(SimulatedDevice(info()), LiveProcessor(info()), max_samples=4)
    with pytest.raises(ValueError, match="No received sample"):
        empty.add_marker("no data")
    empty.device.close()


def test_resource_usage_counts_real_array_storage_and_labels_whole_process_rss():
    ring = RingBuffer(10, 2, 250)
    assert ring.memory_usage()["array_storage_bytes"] == (2*10+10)*8
    assert ring.memory_usage()["retained_sample_value_bytes"] == 0
    ring.append(block(0))
    assert ring.memory_usage()["retained_sample_value_bytes"] == (2*4+4)*8
    session = AcquisitionSession(SimulatedDevice(info()), LiveProcessor(info()), max_samples=4,
                                 block_samples=4, buffer_seconds=.04).start()
    session.wait(3)
    observed = session.resource_usage()
    assert observed["session_ring_array_storage_bytes"] == 2*(2*10+10)*8
    assert "processor windows" in observed["array_scope"]
    assert "Entire current Python process" in observed["process"]["scope"]
    if platform.system() == "Linux":
        assert observed["process"]["process_rss_bytes"] > 0
        assert observed["process"]["process_peak_rss_bytes"] > 0
        assert "Linux KiB converted" in observed["process"]["peak_rss_source"]
    assert "no equivalence" in observed["process"]["clock_note"]


def test_unavailable_platform_resource_values_remain_null(monkeypatch):
    from biosignal_lab.live import resources
    monkeypatch.setattr(resources.platform, "system", lambda: "Unsupported")
    observed = process_memory_usage()
    assert observed["process_rss_bytes"] is None and observed["process_peak_rss_bytes"] is None
    assert observed["current_rss_source"] is None
