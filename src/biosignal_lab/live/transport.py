"""Explicit, bounded JSON framing for a custom TCP acquisition protocol.

This adapter is not an OpenBCI/ADS1299 protocol. A gateway must supply actual
units, synchronized sample timestamps, and monotonically increasing sequence
indices. Network transport is plaintext; use only on trusted local networks or
provide an authenticated encrypted socket established by the caller.
"""
from __future__ import annotations

import json
import inspect
import socket
import struct
from urllib.parse import urlsplit

import numpy as np

from .core import SampleBlock, StreamInfo


def encode_frame(block: SampleBlock, max_bytes: int = 1_048_576) -> bytes:
    payload = json.dumps({"data": block.data.tolist(), "timestamps": block.timestamps.tolist(),
                          "start_sample": int(block.start_sample)}, allow_nan=False,
                         separators=(",", ":")).encode("utf-8")
    if len(payload) > max_bytes:
        raise ValueError("Frame exceeds byte limit")
    return struct.pack("!I", len(payload)) + payload


def _decode_payload(payload: bytes, info: StreamInfo, n_samples: int) -> SampleBlock:
    document = json.loads(payload)
    if not isinstance(document, dict) or set(document) != {"data", "timestamps", "start_sample"}:
        raise ValueError("Unexpected frame schema")
    block = SampleBlock(**document)
    if block.data.shape[0] != len(info.channels) or block.data.shape[1] > n_samples:
        raise ValueError("Frame channel count or sample limit mismatch")
    return block


def _decode_message(message, info: StreamInfo, n_samples: int, max_bytes: int) -> SampleBlock:
    if not isinstance(message, bytes) or not 4 < len(message) <= max_bytes:
        raise ValueError("Expected a bounded binary acquisition frame")
    length = struct.unpack("!I", message[:4])[0]
    if length != len(message) - 4:
        raise ValueError("Frame length differs from message size")
    return _decode_payload(message[4:], info, n_samples)


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
            return _decode_payload(self._exact(length), self.info, n_samples)
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


class UDPDevice:
    """One bounded binary frame per datagram on a caller-connected UDP socket.

    The socket must be connected to one explicit peer; no wildcard peer discovery
    is performed. There is no retransmission, encryption or authentication.
    Process received blocks through RingBuffer/LiveProcessor to detect sequence
    gaps and reordering. This is a custom gateway protocol, not a board driver.
    """

    def __init__(self, connection: socket.socket, info: StreamInfo, timeout: float = 2., max_bytes: int = 65507):
        if not np.isfinite(timeout) or timeout <= 0 or isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or not 5 <= max_bytes <= 65507:
            raise ValueError("Positive timeout and UDP frame limit of 5..65507 bytes required")
        try:
            connection.getpeername()
        except OSError as exc:
            raise ValueError("UDP socket must be connected to one explicit peer") from exc
        if connection.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE) != socket.SOCK_DGRAM:
            raise ValueError("UDP acquisition requires a datagram socket")
        self._socket, self.info, self.max_bytes = connection, info, max_bytes
        connection.settimeout(timeout)
        self._closed = False

    def read(self, n_samples: int = 1_000_000) -> SampleBlock:
        if self._closed:
            raise RuntimeError("UDP device is closed")
        if isinstance(n_samples, bool) or not isinstance(n_samples, int) or n_samples < 1:
            raise ValueError("n_samples must be positive")
        try:
            # An extra byte detects truncated oversized datagrams portably.
            message = self._socket.recv(self.max_bytes + 1)
            return _decode_message(message, self.info, n_samples, self.max_bytes)
        except (OSError, ValueError, TypeError, KeyError, RecursionError):
            self.close()
            raise

    def close(self):
        self._closed = True
        self._socket.close()


class WebSocketDevice:
    """Synchronous binary acquisition frames with bounded message allocation.

    Prefer connect(), which configures websockets' decompressed message and queue
    limits. A caller-supplied connection must enforce equivalent receive bounds.
    No automatic reconnect or arbitrary plugin deserialization occurs.
    """

    def __init__(self, connection, info: StreamInfo, timeout: float = 2., max_bytes: int = 1_048_576):
        if not np.isfinite(timeout) or timeout <= 0 or isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or not 5 <= max_bytes <= 16_777_216:
            raise ValueError("Positive timeout and frame limit of 5..16777216 bytes required")
        self._connection, self.info, self.timeout, self.max_bytes = connection, info, timeout, max_bytes
        self._closed = False
        self._context_manager = None

    @classmethod
    def connect(cls, url: str, info: StreamInfo, timeout: float = 2., max_bytes: int = 1_048_576):
        parts = urlsplit(url)
        if parts.scheme not in ("ws", "wss") or not parts.hostname or parts.username or parts.password or parts.fragment:
            raise ValueError("Explicit ws/wss URL without embedded credentials or fragment required")
        if parts.scheme == "ws" and parts.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("Remote WebSocket acquisition requires wss transport")
        # Validate limits before opening any connection.
        cls(None, info, timeout, max_bytes)
        try:
            from websockets.sync.client import connect
        except ImportError as exc:
            raise RuntimeError("WebSocket acquisition requires optional websockets>=15") from exc
        if "max_queue" not in inspect.signature(connect).parameters:
            raise RuntimeError("WebSocket acquisition requires websockets>=15 with bounded receive queue")
        options = {"open_timeout": timeout, "close_timeout": min(timeout, 1.),
                   "max_size": max_bytes, "max_queue": 1, "compression": None}
        if "proxy" in inspect.signature(connect).parameters:
            # Local devices must not be routed through an HTTP egress proxy.
            # Remote TLS connections retain the configured proxy route.
            if parts.hostname in ("localhost", "127.0.0.1", "::1"):
                options["proxy"] = None
        context = connect(url, **options)
        connection = context.__enter__()
        device = cls(connection, info, timeout, max_bytes)
        device._context_manager = context
        return device

    def read(self, n_samples: int = 1_000_000) -> SampleBlock:
        if self._closed:
            raise RuntimeError("WebSocket device is closed")
        if isinstance(n_samples, bool) or not isinstance(n_samples, int) or n_samples < 1:
            raise ValueError("n_samples must be positive")
        try:
            message = self._connection.recv(timeout=self.timeout)
            return _decode_message(message, self.info, n_samples, self.max_bytes)
        except Exception:
            self.close()
            raise

    def close(self):
        if not self._closed:
            self._closed = True
            if self._context_manager is not None:
                self._context_manager.__exit__(None, None, None)
            else:
                self._connection.close()
