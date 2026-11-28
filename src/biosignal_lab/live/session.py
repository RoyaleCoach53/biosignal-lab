"""Bounded cancellable acquisition worker without implicit reconnection."""
from __future__ import annotations

from threading import Event, RLock, Thread
from time import monotonic
from copy import deepcopy

import numpy as np

from .core import Device, RingBuffer
from .processing import LiveProcessor
from .events import EventMarker
from .recording import save_recording
from .resources import process_memory_usage


class AcquisitionSession:
    """Own one device for one finite capture and expose safe polling snapshots.

    Devices must use bounded read timeouts. stop() requests cancellation and
    waits for the current read; it raises rather than claiming stopped if a
    third-party/native read remains blocked. A session cannot be restarted:
    reconnect with a new device, processor and session. pace=True is intended
    for simulated/playback devices, not physical acquisition timing control.
    """

    def __init__(self, device: Device, processor: LiveProcessor, max_samples: int,
                 block_samples: int = 50, buffer_seconds: float = 10., pace: bool = False,
                 max_idle_timeouts: int = 10, max_markers: int = 1000):
        if device.info != processor.info:
            raise ValueError("Device and processor metadata must match exactly")
        if any(isinstance(x, bool) or not isinstance(x, int) or x < 1 for x in (max_samples, block_samples, max_idle_timeouts)):
            raise ValueError("Positive integer capture limit and block size required")
        if not np.isfinite(buffer_seconds) or buffer_seconds <= 0:
            raise ValueError("buffer_seconds must be positive and finite")
        if isinstance(max_markers, bool) or not isinstance(max_markers, int) or not 1 <= max_markers <= 1000:
            raise ValueError("max_markers must be an integer from 1 to 1000")
        capacity = round(buffer_seconds * device.info.sfreq)
        self.buffer = RingBuffer(capacity, len(device.info.channels), device.info.sfreq)
        self.raw_buffer = RingBuffer(capacity, len(device.info.channels), device.info.sfreq)
        self.device, self.processor = device, processor
        self.max_samples, self.block_samples, self.pace = max_samples, block_samples, pace
        self.max_idle_timeouts = max_idle_timeouts
        self.max_markers = max_markers
        self._markers: list[EventMarker] = []
        self._stop = Event()
        self._lock = RLock()
        self._thread = None
        self._state = "created"
        self._received = self._timeouts = self._blocks = 0
        self._error_type = None
        self._last_result = None
        self._started_at = None
        self._ended_at = None

    def start(self):
        with self._lock:
            if self._state != "created":
                raise RuntimeError("A session can start only once; reconnect explicitly")
            self._state = "running"
            self._started_at = monotonic()
            self._thread = Thread(target=self._run, name="biosignal-acquisition", daemon=True)
            self._thread.start()
        return self

    def _run(self):
        final = "completed"
        idle = 0
        try:
            while self._received < self.max_samples and not self._stop.is_set():
                beginning = monotonic()
                try:
                    block = self.device.read(min(self.block_samples, self.max_samples-self._received))
                except TimeoutError:
                    with self._lock:
                        self._timeouts += 1
                    idle += 1
                    if idle >= self.max_idle_timeouts:
                        final = "idle_timeout"
                        break
                    # A faulty immediate-timeout adapter must not create a hot spin.
                    self._stop.wait(.01)
                    continue
                if self._stop.is_set():
                    break
                idle = 0
                if block.data.shape[1] > min(self.block_samples, self.max_samples-self._received):
                    raise ValueError("Device exceeded requested capture block size")
                result = self.processor.process(block)
                incoming = tuple(getattr(self.device, "last_markers", ()))
                for marker in incoming:
                    if not isinstance(marker, EventMarker):
                        raise ValueError("Acquisition events must carry validated sample-clock provenance")
                    EventMarker.from_record(marker.to_dict(), self.device.info, block)
                with self._lock:
                    if len(self._markers) + len(incoming) > self.max_markers:
                        raise ValueError("Session marker limit exceeded; no events silently discarded")
                    self.raw_buffer.append(block)
                    self.buffer.append(result.block)
                    self._markers.extend(incoming)
                    self._received += block.data.shape[1]
                    self._blocks += 1
                    self._last_result = result
                if self.pace:
                    self._stop.wait(max(0., block.data.shape[1]/self.device.info.sfreq - (monotonic()-beginning)))
            if self._stop.is_set():
                final = "stopped"
        except EOFError:
            final = "disconnected"
        except Exception as exc:
            final = "fault"
            # Do not expose arbitrary adapter exceptions containing credentials/paths.
            with self._lock:
                self._error_type = type(exc).__name__
        finally:
            try:
                self.device.close()
            except Exception as exc:
                final = "fault"
                with self._lock:
                    self._error_type = type(exc).__name__
            with self._lock:
                self._state = final
                self._ended_at = monotonic()

    def wait(self, timeout: float = 2.):
        if not np.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive and finite")
        with self._lock:
            thread = self._thread
        if thread is None:
            raise RuntimeError("Session has not started")
        thread.join(timeout)
        if thread.is_alive():
            raise TimeoutError("Acquisition worker remains active; no stopped-state claim")
        return self.status()

    def stop(self, timeout: float = 2.):
        with self._lock:
            if self._thread is None:
                raise RuntimeError("Session has not started")
        self._stop.set()
        return self.wait(timeout)

    def snapshot(self):
        with self._lock:
            return self.buffer.snapshot()

    def raw_snapshot(self):
        """Latest contiguous native-unit input window, before causal filtering."""
        with self._lock:
            return self.raw_buffer.snapshot()

    def add_marker(self, label: str, sample: int | None = None) -> EventMarker:
        """Annotate an actual retained input sample; never infer a host clock offset.

        Omitting sample explicitly means the latest committed received sample,
        not the physiological occurrence time of the caller's button press.
        Missing/evicted sample indices cannot be annotated using guessed times.
        """
        with self._lock:
            if len(self._markers) >= self.max_markers:
                raise ValueError("Session marker limit exceeded")
            block = self.raw_buffer.snapshot()
            if block is None:
                raise ValueError("No received sample is available for an event marker")
            marker = EventMarker.from_block(self.device.info, block, label, sample)
            self._markers.append(marker)
            return marker

    def markers(self) -> tuple[EventMarker, ...]:
        with self._lock:
            return tuple(self._markers)

    def checkpoint(self, path):
        """Save a new bounded raw window+events; never serialize a live process.

        The saved window can be recovered with PlaybackDevice and a new session.
        Historical events outside this retained contiguous window are counted
        explicitly in the returned summary, not exported with invented samples.
        """
        with self._lock:
            block = self.raw_buffer.snapshot()
            if block is None:
                raise ValueError("No received samples to checkpoint")
            markers = [m.to_dict() for m in self._markers if block.start_sample <= m.sample < block.stop_sample]
            omitted = len(self._markers) - len(markers)
        save_recording(path, self.device.info, block, markers)
        return {"start_sample": block.start_sample, "stop_sample": block.stop_sample,
                "clock": self.device.info.clock, "sample_stage": "raw input before causal processing",
                "markers_saved": len(markers), "markers_outside_retained_window": omitted,
                "recovery": "Create PlaybackDevice and a new processor/session; active connections are not restored"}

    def resource_usage(self):
        raw = self.raw_buffer.memory_usage()
        processed = self.buffer.memory_usage()
        return {"raw_ring": raw, "processed_ring": processed,
                "session_ring_array_storage_bytes": raw["array_storage_bytes"] + processed["array_storage_bytes"],
                "array_scope": "Two fixed session rings only; processor windows, filter state, snapshots and Python objects are additional",
                "process": process_memory_usage()}

    def status(self):
        with self._lock:
            elapsed = 0. if self._started_at is None else (self._ended_at or monotonic()) - self._started_at
            return {"state": self._state, "received_samples": self._received,
                    "blocks": self._blocks, "read_timeouts": self._timeouts,
                    "error_type": self._error_type, "stop_requested": self._stop.is_set(),
                    "elapsed_wall_seconds": elapsed, "pace_simulation": self.pace,
                    "markers_count": len(self._markers), "markers_limit": self.max_markers,
                    "buffer": self.buffer.diagnostics(),
                    "last_processing": None if self._last_result is None else deepcopy(self._last_result.diagnostics)}
