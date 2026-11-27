"""Explicit, bounded JSON framing for a custom TCP acquisition protocol.

This adapter is not an OpenBCI/ADS1299 protocol. A gateway must supply actual
units, synchronized sample timestamps, and monotonically increasing sequence
indices. Network transport is plaintext; use only on trusted local networks or
provide an authenticated encrypted socket established by the caller.
"""
from __future__ import annotations

import json
import socket
import struct

import numpy as np

from .core import SampleBlock, StreamInfo


def encode_frame(block: SampleBlock, max_bytes: int = 1_048_576) -> bytes:
    payload = json.dumps({"data": block.data.tolist(), "timestamps": block.timestamps.tolist(),
                          "start_sample": int(block.start_sample)}, allow_nan=False,
                         separators=(",", ":")).encode("utf-8")
    if len(payload) > max_bytes:
        raise ValueError("Frame exceeds byte limit")
    return struct.pack("!I", len(payload)) + payload


class TCPDevice:
    """Read one complete length-prefixed block per call; timeout never retries.

    A failed/incomplete frame closes the connection to prevent framing confusion.
    Reconnection requires a new instance and a deliberate new acquisition session.
    """

    def __init__(self, connection: socket.socket, info: StreamInfo, timeout: float = 2., max_bytes: int = 1_048_576):
        if not np.isfinite(timeout) or timeout <= 0 or isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1 or max_bytes > 16_777_216:
            raise ValueError("Positive timeout and frame limit <=16MiB required")
        self.info, self._socket, self.max_bytes = info, connection, max_bytes
        self._socket.settimeout(timeout)
        self._closed = False

    def _exact(self, n: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < n:
            part = self._socket.recv(n - len(chunks))
            if not part:
                raise EOFError("Acquisition peer disconnected mid-frame")
            chunks.extend(part)
        return bytes(chunks)

    def read(self, n_samples: int = 1_000_000) -> SampleBlock:
        if self._closed:
            raise RuntimeError("TCP device is closed")
        if isinstance(n_samples, bool) or not isinstance(n_samples, int) or n_samples < 1:
            raise ValueError("n_samples must be positive; TCP returns one whole bounded frame")
        try:
            length = struct.unpack("!I", self._exact(4))[0]
            if not 1 <= length <= self.max_bytes:
                raise ValueError("Frame exceeds configured byte limit")
            payload = json.loads(self._exact(length))
            if not isinstance(payload, dict) or set(payload) != {"data", "timestamps", "start_sample"}:
                raise ValueError("Unexpected frame schema")
            block = SampleBlock(**payload)
            if block.data.shape[0] != len(self.info.channels) or block.data.shape[1] > n_samples:
                raise ValueError("Frame channel count or sample limit mismatch")
            return block
        except (OSError, EOFError, ValueError, TypeError, KeyError, RecursionError):
            self.close()
            raise

    def close(self):
        self._closed = True
        self._socket.close()


class _SerialConnection:
    """Map an already-open pyserial object to the bounded framing transport."""

    def __init__(self, port):
        self.port = port

    def settimeout(self, timeout):
        self.port.timeout = timeout

    def recv(self, n):
        data = self.port.read(n)
        if not data:
            raise TimeoutError("Serial frame timed out; reconnect with a fresh parser")
        return data

    def close(self):
        self.port.close()


class SerialDevice(TCPDevice):
    """Custom length-prefixed JSON over an already-open pyserial port.

    This is software framing, not a driver for an arbitrary USB/serial board.
    Timeouts close the port: an incomplete frame must never be retried using
    ambiguous parser state. Physical serial devices have not been verified.
    """

    def __init__(self, port, info: StreamInfo, timeout: float = 2., max_bytes: int = 1_048_576):
        super().__init__(_SerialConnection(port), info, timeout, max_bytes)
