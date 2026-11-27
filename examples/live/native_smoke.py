"""Opt-in native-library verification using synthetic/local streams, never hardware."""
from __future__ import annotations

import argparse
import json
from importlib.metadata import version
import time
from uuid import uuid4

import numpy as np

from biosignal_lab.live import BrainFlowDevice, LSLDevice, SampleBlock, SerialDevice, StreamInfo, encode_frame


def brainflow_smoke():
    from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams
    BoardShim.disable_board_logger()
    identifier = BoardIds.SYNTHETIC_BOARD.value
    board = BoardShim(identifier, BrainFlowInputParams())
    rows = BoardShim.get_eeg_channels(identifier)
    info = StreamInfo(BoardShim.get_sampling_rate(identifier), tuple(f"EEG{i+1}" for i in range(len(rows))),
                      ("uV",) * len(rows), clock="brainflow_synthetic_unix_seconds")
    board.prepare_session()
    started = False
    adapter = None
    try:
        board.start_stream(1000)
        started = True
        adapter = BrainFlowDevice(board, info, rows, BoardShim.get_timestamp_channel(identifier),
                                  counter_row=BoardShim.get_package_num_channel(identifier), owns_board=True)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                sample = adapter.read(50)
                if sample.data.shape[1] >= 2:
                    return {"library": "brainflow", "version": version("brainflow"),
                            "source": "native SYNTHETIC_BOARD; no physical hardware",
                            "channels": len(info.channels), "sfreq_hz": info.sfreq,
                            "samples": sample.data.shape[1], "finite": bool(np.isfinite(sample.data).all()),
                            "timestamps_increasing": bool(np.all(np.diff(sample.timestamps) > 0))}
            except TimeoutError:
                pass
            time.sleep(.02)
        raise RuntimeError("No synthetic BrainFlow samples before deadline")
    finally:
        if adapter is not None:
            adapter.close()
        else:
            try:
                if started:
                    board.stop_stream()
            finally:
                board.release_session()


def lsl_smoke():
    import pylsl
    descriptor = pylsl.StreamInfo("biosignal-local-smoke", "EEG", 2, 250, "float32", "biosignal-" + str(uuid4()))
    outlet = pylsl.StreamOutlet(descriptor)
    matches = pylsl.resolve_byprop("source_id", descriptor.source_id(), timeout=3)
    if len(matches) != 1:
        raise RuntimeError("Local LSL outlet discovery failed or was ambiguous")
    inlet = pylsl.StreamInlet(matches[0], recover=False)
    adapter = None
    try:
        inlet.open_stream(timeout=3)
        if not outlet.wait_for_consumers(timeout=3):
            raise RuntimeError("Local LSL outlet/inlet failed to connect")
        adapter = LSLDevice(inlet, StreamInfo(250, ("C3", "C4"), ("uV", "uV"), clock="lsl_remote_clock"))
        expected = np.array([[1., 2.], [3., 4.], [5., 6.]])
        outlet.push_chunk(expected.tolist(), timestamp=pylsl.local_clock())
        sample = adapter.read(10)
        np.testing.assert_array_equal(sample.data, expected.T)
        return {"library": "pylsl", "version": version("pylsl"), "liblsl_version": pylsl.library_version(),
                "source": "local synthetic LSL outlet; no physical hardware",
                "channels": 2, "sfreq_hz": 250, "samples": sample.data.shape[1],
                "sample_values_match": True, "timestamps_increasing": bool(np.all(np.diff(sample.timestamps) > 0))}
    finally:
        if adapter is not None:
            adapter.close()
        else:
            inlet.close_stream()


def serial_smoke():
    import serial
    port = serial.serial_for_url("loop://", timeout=.2)
    info = StreamInfo(250, ("C3", "C4"), ("uV", "uV"), clock="synthetic_seconds")
    expected = SampleBlock(np.arange(8).reshape(2, 4), np.arange(4)/250, 0)
    adapter = SerialDevice(port, info, timeout=.2)
    try:
        port.write(encode_frame(expected))
        actual = adapter.read(10)
        np.testing.assert_array_equal(actual.data, expected.data)
        np.testing.assert_array_equal(actual.timestamps, expected.timestamps)
        return {"library": "pyserial", "version": serial.__version__,
                "source": "pyserial loop:// virtual port; no physical serial hardware",
                "samples": actual.data.shape[1], "channels": 2, "sample_values_match": True,
                "timestamps_match": True}
    finally:
        adapter.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["brainflow", "lsl", "serial"], required=True)
    args = parser.parse_args()
    print(json.dumps({"brainflow": brainflow_smoke, "lsl": lsl_smoke, "serial": serial_smoke}[args.source](), indent=2))


if __name__ == "__main__":
    main()
