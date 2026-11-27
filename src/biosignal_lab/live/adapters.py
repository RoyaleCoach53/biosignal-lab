"""Optional acquisition-library adapters with explicit ownership and clock rules.

The software contracts are tested using protocol fakes. They are not evidence
of successful acquisition from any physical board or network LSL outlet.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from .core import SampleBlock, StreamInfo


def _read_count(n_samples, n_channels):
    if isinstance(n_samples, bool) or not isinstance(n_samples, int) or n_samples < 1 or n_samples * n_channels > 1_000_000:
        raise ValueError("Read must request 1..1000000 channel values")


class LSLDevice:
    """Adapt a caller-supplied pylsl inlet; preserve explicit channel units.

    LSL transports sample timestamps, but does not supply a source sample counter.
    Generated indices count received samples only: sequence-based source-loss
    detection is unavailable. Timestamp discontinuities remain observable.
    """

    source_loss_detection = "timestamp gaps only; source sample counters unavailable"

    def __init__(self, inlet, info: StreamInfo, timeout: float = 2., correct_clock: bool = False):
        if not np.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        descriptor = inlet.info(timeout=timeout)
        if descriptor.channel_count() != len(info.channels) or not np.isclose(descriptor.nominal_srate(), info.sfreq, rtol=1e-6):
            raise ValueError("LSL channel count/sample rate does not match explicit metadata")
        self._inlet, self.timeout, self.correct_clock = inlet, timeout, correct_clock
        self.info = replace(info, clock="lsl_local_clock") if correct_clock else info
        self._next = 0
        self._last_time = None
        self._closed = False
        self.last_clock_correction_s = None

    @classmethod
    def from_stream(cls, info: StreamInfo, stream_name: str, timeout: float = 2., correct_clock: bool = False):
        """Resolve an exact LSL name; refuse ambiguous or absent streams.

        Requires the optional pylsl package and its supported liblsl runtime.
        No discovery occurs merely by importing this module.
        """
        if not isinstance(stream_name, str) or not stream_name:
            raise ValueError("An explicit nonempty LSL stream name is required")
        if not np.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        try:
            import pylsl
        except (ImportError, RuntimeError) as exc:
            raise RuntimeError("LSL requires optional pylsl and a working liblsl runtime") from exc
        matches = pylsl.resolve_byprop("name", stream_name, timeout=timeout)
        if len(matches) != 1:
            raise RuntimeError("Expected exactly one matching LSL stream")
        inlet = pylsl.StreamInlet(matches[0], max_buflen=2, recover=False)
        try:
            return cls(inlet, info, timeout, correct_clock)
        except Exception:
            inlet.close_stream()
            raise

    def read(self, n_samples: int) -> SampleBlock:
        if self._closed:
            raise RuntimeError("LSL inlet is closed; reconnect explicitly")
        _read_count(n_samples, len(self.info.channels))
        try:
            samples, timestamps = self._inlet.pull_chunk(timeout=self.timeout, max_samples=n_samples)
            if len(timestamps) == 0:
                # No samples is not proof of disconnection; leave the inlet usable.
                raise TimeoutError("No LSL samples before timeout")
            data = np.asarray(samples, dtype=float)
            if data.shape != (len(timestamps), len(self.info.channels)) or len(timestamps) > n_samples:
                raise ValueError("LSL samples/metadata or requested limit mismatch")
            timestamps = np.asarray(timestamps, dtype=float)
            if self.correct_clock:
                correction = float(self._inlet.time_correction(timeout=self.timeout))
                if not np.isfinite(correction):
                    raise ValueError("LSL clock correction is not finite")
                self.last_clock_correction_s = correction
                timestamps = timestamps + correction
            block = SampleBlock(data.T, timestamps, self._next)
            if self._last_time is not None and block.timestamps[0] <= self._last_time:
                raise ValueError("LSL timestamp clock moved backwards")
            self._next = block.stop_sample
            self._last_time = block.timestamps[-1]
            return block
        except TimeoutError:
            raise
        except Exception:
            self.close()
            raise

    def close(self):
        if not self._closed:
            self._closed = True
            self._inlet.close_stream()


class BrainFlowDevice:
    """Adapt a started BoardShim, with explicit descriptor row indices.

    The caller creates/prepares/starts the board using BrainFlow's documented
    board-specific parameters and is responsible for units and channel labels.
    With owns_board=True, close stops streaming and releases the session. Without
    ownership, this adapter never closes a caller's shared hardware session.
    """

    def __init__(self, board, info: StreamInfo, signal_rows, timestamp_row: int,
                 counter_row: int | None = None, counter_modulus: int = 256,
                 owns_board: bool = False):
        rows = tuple(signal_rows)
        all_rows = rows + (timestamp_row,) + (() if counter_row is None else (counter_row,))
        if len(rows) != len(info.channels) or len(set(all_rows)) != len(all_rows) or any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in all_rows):
            raise ValueError("Distinct nonnegative channel, timestamp and optional counter rows required")
        if isinstance(counter_modulus, bool) or not isinstance(counter_modulus, int) or counter_modulus < 2:
            raise ValueError("counter_modulus must be an integer >=2")
        self.info, self._board, self.rows = info, board, rows
        self.timestamp_row, self.counter_row, self.counter_modulus = timestamp_row, counter_row, counter_modulus
        self.owns_board = owns_board
        self._next = 0
        self._last_counter = None
        self._last_time = None
        self._closed = False
        self.source_loss_detection = "source counter with modulo ambiguity" if counter_row is not None else "timestamp gaps only; source counter not configured"

    def read(self, n_samples: int) -> SampleBlock:
        if self._closed:
            raise RuntimeError("BrainFlow adapter is closed; start a fresh session to reconnect")
        _read_count(n_samples, len(self.info.channels))
        try:
            values = np.asarray(self._board.get_board_data(n_samples), dtype=float)
            max_row = max(self.rows + (self.timestamp_row,) + (() if self.counter_row is None else (self.counter_row,)))
            if values.ndim != 2 or values.shape[0] <= max_row or values.shape[1] > n_samples:
                raise ValueError("BrainFlow matrix shape or sample limit mismatch")
            if values.shape[1] == 0:
                raise TimeoutError("BrainFlow buffer currently contains no samples")
            start = self._next
            if self.counter_row is not None:
                counters = values[self.counter_row]
                if not np.isfinite(counters).all() or np.any(counters != np.floor(counters)) or np.any((counters < 0) | (counters >= self.counter_modulus)):
                    raise ValueError("Invalid BrainFlow packet counters")
                if np.any(np.mod(np.diff(counters), self.counter_modulus) != 1):
                    raise ValueError("Within-block packet loss/reordering; split source into contiguous blocks")
                if self._last_counter is not None:
                    advance = int((counters[0] - self._last_counter) % self.counter_modulus)
                    if advance == 0:
                        raise ValueError("Duplicate or modulo-ambiguous packet counter")
                    if advance > self.counter_modulus // 2:
                        raise ValueError("Out-of-order counter or gap too large to disambiguate")
                    start += advance - 1
                self._last_counter = int(counters[-1])
            block = SampleBlock(values[list(self.rows)], values[self.timestamp_row], start)
            if self._last_time is not None and block.timestamps[0] <= self._last_time:
                raise ValueError("BrainFlow timestamp clock moved backwards")
            self._next = block.stop_sample
            self._last_time = block.timestamps[-1]
            return block
        except TimeoutError:
            raise
        except Exception:
            self.close()
            raise

    def close(self):
        if not self._closed:
            self._closed = True
            if self.owns_board:
                try:
                    self._board.stop_stream()
                finally:
                    self._board.release_session()
