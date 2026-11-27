from threading import Event

import numpy as np
import pytest

from biosignal_lab.live import AcquisitionSession, LiveProcessor, SampleBlock, SimulatedDevice, StreamInfo


def info():
    return StreamInfo(250, ("C3", "C4"), ("uV", "uV"), clock="simulated_seconds")


def test_finite_acquisition_worker_preserves_buffer_limits_and_completes():
    session = AcquisitionSession(SimulatedDevice(info()), LiveProcessor(info()),
                                 max_samples=127, block_samples=25, buffer_seconds=.2)
    session.start()
    status = session.wait(3)
    assert status["state"] == "completed"
    assert status["received_samples"] == 127 and status["blocks"] == 6
    assert status["buffer"]["retained_samples"] == 50
    snapshot = session.snapshot()
    assert snapshot.data.shape == (2, 50) and snapshot.start_sample == 77
    status["last_processing"]["input_rms"][0] = -1
    assert session.status()["last_processing"]["input_rms"][0] >= 0
    with pytest.raises(RuntimeError, match="only once"):
        session.start()


def test_paced_simulation_stop_cancels_wait_and_closes_device():
    device = SimulatedDevice(info())
    session = AcquisitionSession(device, LiveProcessor(info()), max_samples=10000,
                                 block_samples=100, pace=True).start()
    status = session.stop(2)
    assert status["state"] == "stopped" and status["stop_requested"]
    assert status["received_samples"] < 10000
    with pytest.raises(RuntimeError, match="closed"):
        device.read(1)


def test_idle_timeouts_are_bounded_and_disconnect_requires_new_session():
    class IdleDevice:
        info = info()
        closed = False

        def read(self, n):
            raise TimeoutError("no data")

        def close(self):
            self.closed = True

    idle = IdleDevice()
    session = AcquisitionSession(idle, LiveProcessor(info()), max_samples=100,
                                 max_idle_timeouts=2).start()
    status = session.wait(2)
    assert status["state"] == "idle_timeout" and status["read_timeouts"] == 2
    assert idle.closed

    class DisconnectedDevice(IdleDevice):
        def read(self, n):
            raise EOFError("device gone")

    disconnected = AcquisitionSession(DisconnectedDevice(), LiveProcessor(info()), max_samples=100).start()
    assert disconnected.wait(2)["state"] == "disconnected"


def test_blocking_native_read_never_claims_stopped_before_worker_exits():
    entered, release = Event(), Event()

    class BlockingDevice:
        info = info()

        def read(self, n):
            entered.set()
            release.wait(3)
            return SampleBlock(np.zeros((2, 1)), np.array([0.]), 0)

        def close(self):
            pass

    session = AcquisitionSession(BlockingDevice(), LiveProcessor(info()), max_samples=100).start()
    assert entered.wait(1)
    try:
        with pytest.raises(TimeoutError, match="remains active"):
            session.stop(.01)
        assert session.status()["state"] == "running"
        assert session.status()["stop_requested"]
    finally:
        release.set()
    assert session.wait(2)["state"] == "stopped"
