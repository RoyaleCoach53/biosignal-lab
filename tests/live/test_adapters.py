import sys
from types import SimpleNamespace

import numpy as np
import pytest

from biosignal_lab.live import BrainFlowDevice, LSLDevice, SampleBlock, SerialDevice, StreamInfo, encode_frame


def info():
    return StreamInfo(250, ("C3", "C4"), ("uV", "uV"), clock="device_seconds")


class FakeInlet:
    def __init__(self, chunks):
        self.chunks = iter(chunks)
        self.closed = 0

    def info(self, timeout=None):
        return SimpleNamespace(channel_count=lambda: 2, nominal_srate=lambda: 250)

    def pull_chunk(self, timeout, max_samples):
        chunk = next(self.chunks)
        if isinstance(chunk, Exception):
            raise chunk
        return chunk

    def time_correction(self, timeout):
        return .25

    def close_stream(self):
        self.closed += 1


def test_lsl_clock_correction_and_empty_read_timeout_preserve_inlet():
    inlet = FakeInlet([([], []), ([[1, 2], [3, 4]], [1, 1.004])])
    device = LSLDevice(inlet, info(), correct_clock=True)
    with pytest.raises(TimeoutError):
        device.read(10)
    assert inlet.closed == 0
    result = device.read(10)
    np.testing.assert_array_equal(result.data, [[1, 3], [2, 4]])
    np.testing.assert_allclose(result.timestamps, [1.25, 1.254])
    assert device.info.clock == "lsl_local_clock"
    assert device.last_clock_correction_s == .25
    device.close()
    device.close()
    assert inlet.closed == 1


def test_lsl_disconnect_and_backwards_clock_close_connection():
    inlet = FakeInlet([([[1, 2]], [1]), ([[1, 2]], [.9])])
    device = LSLDevice(inlet, info())
    device.read(1)
    with pytest.raises(ValueError, match="backwards"):
        device.read(1)
    assert inlet.closed == 1
    with pytest.raises(RuntimeError, match="closed"):
        device.read(1)
    disconnected = FakeInlet([OSError("peer vanished")])
    with pytest.raises(OSError):
        LSLDevice(disconnected, info()).read(1)
    assert disconnected.closed == 1


def test_lsl_factory_refuses_ambiguous_discovery_and_disables_recovery(monkeypatch):
    inlet = FakeInlet([])
    calls = []
    fake = SimpleNamespace(resolve_byprop=lambda *args, **kw: ["one"],
                           StreamInlet=lambda stream, **kw: (calls.append(kw) or inlet))
    monkeypatch.setitem(sys.modules, "pylsl", fake)
    device = LSLDevice.from_stream(info(), "research-stream")
    assert calls == [{"max_buflen": 2, "recover": False}]
    device.close()
    fake.resolve_byprop = lambda *args, **kw: ["one", "two"]
    with pytest.raises(RuntimeError, match="exactly one"):
        LSLDevice.from_stream(info(), "research-stream")


class FakeBoard:
    def __init__(self, chunks, stop_fails=False):
        self.chunks = iter(chunks)
        self.stopped = self.released = 0
        self.stop_fails = stop_fails

    def get_board_data(self, n):
        chunk = next(self.chunks)
        if isinstance(chunk, Exception):
            raise chunk
        return chunk

    def stop_stream(self):
        self.stopped += 1
        if self.stop_fails:
            raise OSError("stop failed")

    def release_session(self):
        self.released += 1


def board_data(counters, start_time):
    n = len(counters)
    return np.array([np.arange(n), np.arange(n)+10, np.arange(n)/250+start_time, counters])


def test_brainflow_counter_wrap_and_gap_are_preserved_in_sample_indices():
    board = FakeBoard([board_data([254, 255, 0, 1], 1), board_data([4, 5], 1.024)])
    device = BrainFlowDevice(board, info(), [0, 1], 2, counter_row=3)
    first = device.read(10)
    second = device.read(10)
    assert first.start_sample == 0 and first.stop_sample == 4
    assert second.start_sample == 6  # Missing counters 2 and 3 are not concealed.
    np.testing.assert_array_equal(second.data, [[0, 1], [10, 11]])
    device.close()
    assert board.stopped == board.released == 0  # Caller retains ownership.


def test_brainflow_internal_loss_rejected_and_owned_session_released():
    board = FakeBoard([board_data([1, 3], 1)])
    device = BrainFlowDevice(board, info(), [0, 1], 2, counter_row=3, owns_board=True)
    with pytest.raises(ValueError, match="Within-block"):
        device.read(10)
    assert board.stopped == board.released == 1
    with pytest.raises(RuntimeError, match="closed"):
        device.read(10)


def test_brainflow_empty_buffer_is_retryable_but_disconnect_closes():
    board = FakeBoard([np.empty((4, 0)), OSError("connection lost")])
    device = BrainFlowDevice(board, info(), [0, 1], 2, owns_board=True)
    with pytest.raises(TimeoutError):
        device.read(10)
    assert board.stopped == 0
    with pytest.raises(OSError):
        device.read(10)
    assert board.stopped == board.released == 1


def test_owned_brainflow_cleanup_releases_even_when_stop_fails():
    board = FakeBoard([], stop_fails=True)
    device = BrainFlowDevice(board, info(), [0, 1], 2, owns_board=True)
    with pytest.raises(OSError, match="stop failed"):
        device.close()
    assert board.released == 1
    device.close()
    assert board.released == 1


def test_serial_framing_partial_reads_and_timeout_cleanup():
    sample = SampleBlock(np.ones((2, 4)), np.arange(4)/250, 0)

    class Port:
        def __init__(self):
            self.pending = bytearray(encode_frame(sample))
            self.timeout = None
            self.closed = False

        def read(self, n):
            chunk = bytes(self.pending[:min(n, 7)])
            del self.pending[:len(chunk)]
            return chunk

        def close(self):
            self.closed = True

    port = Port()
    adapter = SerialDevice(port, info(), timeout=.1)
    result = adapter.read(10)
    np.testing.assert_array_equal(result.data, sample.data)
    assert port.timeout == .1
    with pytest.raises(TimeoutError, match="Serial"):
        adapter.read(10)
    assert port.closed
