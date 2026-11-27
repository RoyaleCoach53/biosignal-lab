import socket
import struct
from threading import Thread

import numpy as np
import pytest

from biosignal_lab.live import RingBuffer, SampleBlock, StreamInfo, UDPDevice, WebSocketDevice, encode_frame


def info():
    return StreamInfo(250, ("C3", "C4"), ("uV", "uV"), clock="synthetic_seconds")


def sample(start):
    return SampleBlock(np.tile(np.arange(start, start+4), (2, 1)), np.arange(start, start+4)/250, start)


def udp_pair():
    sender, receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM), socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sender.bind(("127.0.0.1", 0))
    receiver.bind(("127.0.0.1", 0))
    sender.connect(receiver.getsockname())
    receiver.connect(sender.getsockname())
    return sender, receiver


def test_udp_real_loopback_frames_gap_detection_and_reordering():
    sender, receiver = udp_pair()
    device = UDPDevice(receiver, info())
    ring = RingBuffer(20, 2, 250)
    try:
        for begin in (0, 8):
            sender.send(encode_frame(sample(begin)))
            actual = device.read(10)
            np.testing.assert_array_equal(actual.data, sample(begin).data)
            ring.append(actual)
        assert ring.diagnostics()["dropped_samples"] == 4
        sender.send(encode_frame(sample(4)))
        with pytest.raises(ValueError, match="out-of-order"):
            ring.append(device.read(10))
    finally:
        sender.close()
        device.close()


def test_udp_oversize_malformed_frame_and_timeout_are_closed():
    sender, receiver = udp_pair()
    device = UDPDevice(receiver, info(), max_bytes=64)
    sender.send(b"x"*128)
    with pytest.raises(ValueError, match="bounded"):
        device.read()
    with pytest.raises(RuntimeError, match="closed"):
        device.read()
    sender.close()
    sender, receiver = udp_pair()
    device = UDPDevice(receiver, info(), timeout=.02)
    with pytest.raises(TimeoutError):
        device.read()
    with pytest.raises(RuntimeError, match="closed"):
        device.read()
    sender.close()
    sender, receiver = udp_pair()
    device = UDPDevice(receiver, info())
    sender.send(struct.pack("!I", 5)+b"{}")
    with pytest.raises(ValueError, match="length"):
        device.read()
    sender.close()


def test_udp_requires_explicit_connected_datagram_peer():
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        with pytest.raises(ValueError, match="explicit peer"):
            UDPDevice(receiver, info())
    finally:
        receiver.close()


def test_websocket_real_loopback_binary_values_and_lifecycle():
    from websockets.sync.server import serve

    def handler(connection):
        connection.send(encode_frame(sample(0)))
        connection.send(encode_frame(sample(4)))

    with serve(handler, "127.0.0.1", 0) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        device = None
        try:
            address = server.socket.getsockname()
            device = WebSocketDevice.connect(f"ws://127.0.0.1:{address[1]}", info())
            for begin in (0, 4):
                actual = device.read(10)
                np.testing.assert_array_equal(actual.data, sample(begin).data)
                np.testing.assert_array_equal(actual.timestamps, sample(begin).timestamps)
            device.close()
            with pytest.raises(RuntimeError, match="closed"):
                device.read(10)
        finally:
            if device is not None:
                device.close()
            server.shutdown()
            thread.join(3)
            assert not thread.is_alive()


def test_websocket_real_oversize_message_rejected_at_protocol_limit():
    from websockets.exceptions import ConnectionClosedError
    from websockets.sync.server import serve

    def handler(connection):
        connection.send(b"x"*4096)

    with serve(handler, "127.0.0.1", 0) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        device = None
        try:
            address = server.socket.getsockname()
            device = WebSocketDevice.connect(f"ws://127.0.0.1:{address[1]}", info(), max_bytes=256)
            with pytest.raises(ConnectionClosedError):
                device.read()
            with pytest.raises(RuntimeError, match="closed"):
                device.read()
        finally:
            if device is not None:
                device.close()
            server.shutdown()
            thread.join(3)
            assert not thread.is_alive()


def test_websocket_plaintext_remote_and_embedded_credentials_are_rejected_before_connect():
    for url in ("ws://example.com/device", "wss://user:secret@example.com/device", "http://127.0.0.1/device"):
        with pytest.raises(ValueError):
            WebSocketDevice.connect(url, info())
