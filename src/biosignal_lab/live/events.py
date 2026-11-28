"""Event annotations referencing measured sample timestamps, never guessed clocks."""
from dataclasses import asdict, dataclass
from numbers import Real

import numpy as np

from .core import SampleBlock, StreamInfo


@dataclass(frozen=True)
class EventMarker:
    sample: int
    timestamp: float
    clock: str
    label: str
    source: str = "explicit_sample"

    def __post_init__(self):
        if isinstance(self.sample, bool) or not isinstance(self.sample, (int, np.integer)) or self.sample < 0:
            raise ValueError("Marker sample must be a nonnegative integer")
        if isinstance(self.timestamp, bool) or not isinstance(self.timestamp, Real) or not np.isfinite(self.timestamp):
            raise ValueError("Marker timestamp must be finite device-clock seconds")
        if not isinstance(self.clock, str) or not 1 <= len(self.clock) <= 256:
            raise ValueError("Marker clock must be explicit and bounded")
        if not isinstance(self.label, str) or not 1 <= len(self.label) <= 256:
            raise ValueError("Marker label must contain 1..256 characters")
        if self.source not in ("explicit_sample", "latest_received_sample", "legacy_sample_reference"):
            raise ValueError("Marker source must describe its sample-reference provenance")
        object.__setattr__(self, "sample", int(self.sample))
        object.__setattr__(self, "timestamp", float(self.timestamp))

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_block(cls, info: StreamInfo, block: SampleBlock, label: str, sample: int | None = None):
        source = "latest_received_sample" if sample is None else "explicit_sample"
        index = block.stop_sample - 1 if sample is None else sample
        if isinstance(index, bool) or not isinstance(index, (int, np.integer)) or not block.start_sample <= index < block.stop_sample:
            raise ValueError("Marker sample is absent, dropped or outside the retained contiguous window")
        return cls(int(index), float(block.timestamps[index-block.start_sample]), info.clock, label, source)

    @classmethod
    def from_record(cls, record: dict, info: StreamInfo, block: SampleBlock):
        if not isinstance(record, dict):
            raise ValueError("Marker must be a JSON object")
        if set(record) == {"sample", "label"}:
            marker = cls.from_block(info, block, record["label"], record["sample"])
            return cls(marker.sample, marker.timestamp, marker.clock, marker.label, "legacy_sample_reference")
        if set(record) != {"sample", "timestamp", "clock", "label", "source"}:
            raise ValueError("Marker requires legacy sample/label or complete sample-clock provenance")
        marker = cls(**record)
        expected = cls.from_block(info, block, marker.label, marker.sample)
        if marker.clock != info.clock or marker.timestamp != expected.timestamp:
            raise ValueError("Marker timestamp/clock differs from the referenced recorded sample")
        return marker
