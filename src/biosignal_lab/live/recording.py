"""Non-pickle bounded NPZ recording with explicit stream metadata and markers."""
from __future__ import annotations

from dataclasses import asdict
import io
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np

from .core import SampleBlock, StreamInfo
from ._json import decode_json
from .events import EventMarker


def recording_bytes(info: StreamInfo, block: SampleBlock, markers: list[dict] | None = None,
                    max_values: int = 10_000_000) -> bytes:
    if block.data.shape[0] != len(info.channels) or block.data.size > max_values:
        raise ValueError("Recording channel count or size violates limit")
    markers = [] if markers is None else markers
    if not isinstance(markers, list) or len(markers) > 1000:
        raise ValueError("At most 1000 event markers are supported")
    for marker in markers:
        EventMarker.from_record(marker, info, block)
    metadata = {"schema": "biosignal-live-1", "stream": asdict(info),
                "start_sample": int(block.start_sample), "markers": markers,
                "scope": "Research recording; units and device clock retained, no automatic clock alignment"}
    encoded_metadata = json.dumps(metadata, allow_nan=False)
    if len(encoded_metadata.encode("utf-8")) > 16000:
        raise ValueError("Recording metadata exceeds 16000-byte limit")
    buffer = io.BytesIO()
    np.savez_compressed(buffer, data=block.data, timestamps=block.timestamps,
                        metadata=np.array(encoded_metadata))
    return buffer.getvalue()


def save_recording(path: str | Path, info: StreamInfo, block: SampleBlock,
                   markers: list[dict] | None = None) -> None:
    """Reserve a new file exclusively. Existing files and symlinks are preserved."""
    payload = recording_bytes(info, block, markers)
    with Path(path).open("xb") as destination:
        destination.write(payload)


def load_recording(path: str | Path, max_values: int = 10_000_000) -> tuple[StreamInfo, SampleBlock, list[dict]]:
    if not isinstance(max_values, int) or max_values < 1:
        raise ValueError("max_values must be a positive integer")
    # Bound both compressed file size and total decompressed member size before numpy loads.
    with Path(path).open("rb") as source:
        if source.seek(0, 2) > max_values * 16 + 65536:
            raise ValueError("Recording exceeds size limit")
        source.seek(0)
        with ZipFile(source) as archive:
            members = archive.infolist()
            if sorted(x.filename for x in members) != ["data.npy", "metadata.npy", "timestamps.npy"] or sum(x.file_size for x in members) > max_values * 16 + 65536:
                raise ValueError("Unexpected archive members or decompressed size limit")
            # Validate NPY headers before NumPy allocates memory from their shapes.
            for member in members:
                with archive.open(member) as entry:
                    version = np.lib.format.read_magic(entry)
                    if version == (1, 0):
                        shape, _, dtype = np.lib.format.read_array_header_1_0(entry)
                    elif version == (2, 0):
                        shape, _, dtype = np.lib.format.read_array_header_2_0(entry)
                    else:
                        raise ValueError("Unsupported array format")
                    count = 1
                    for extent in shape:
                        count *= extent
                    if dtype.hasobject or count > max_values or count * dtype.itemsize > member.file_size - entry.tell():
                        raise ValueError("Unsafe array type, shape/size limit or truncated data")
        source.seek(0)
        with np.load(source, allow_pickle=False) as archive:
            raw = archive["metadata"]
            if raw.ndim != 0 or raw.dtype.kind != "U" or raw.itemsize > 65536:
                raise ValueError("Invalid metadata")
            metadata = decode_json(str(raw))
            if not isinstance(metadata, dict) or set(metadata) != {"schema", "stream", "start_sample", "markers", "scope"} or metadata.get("schema") != "biosignal-live-1":
                raise ValueError("Unsupported recording schema")
            stream = metadata["stream"]
            if not isinstance(stream, dict) or set(stream) != {"sfreq", "channels", "units", "modality", "clock"}:
                raise ValueError("Invalid recording stream metadata")
            info = StreamInfo(**stream)
            block = SampleBlock(archive["data"], archive["timestamps"], metadata["start_sample"])
            # Reuse export validation rather than accepting inconsistent markers/shape.
            recording_bytes(info, block, metadata["markers"], max_values=max_values)
            return info, block, metadata["markers"]


class PlaybackDevice:
    """Finite virtual-clock playback, preserving timestamps and sample indices."""

    def __init__(self, path: str | Path):
        self.info, self._block, self.markers = load_recording(path)
        self._cursor = 0
        self._closed = False
        self.last_markers: tuple[EventMarker, ...] = ()

    def read(self, n_samples: int) -> SampleBlock:
        if self._closed:
            raise RuntimeError("Playback is closed")
        if isinstance(n_samples, bool) or not isinstance(n_samples, int) or n_samples < 1:
            raise ValueError("n_samples must be a positive integer")
        begin = self._cursor
        end = min(begin + n_samples, self._block.data.shape[1])
        if begin == end:
            self.last_markers = ()
            raise EOFError("End of recording")
        self._cursor = end
        block = SampleBlock(self._block.data[:, begin:end], self._block.timestamps[begin:end], self._block.start_sample + begin)
        self.last_markers = tuple(EventMarker.from_record(marker, self.info, self._block)
                                  for marker in self.markers if block.start_sample <= marker["sample"] < block.stop_sample)
        return block

    def close(self):
        self._closed = True
