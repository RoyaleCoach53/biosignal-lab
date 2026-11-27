"""Optional BIDS and XDF adapters with explicit clocks, units and provenance."""

from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import struct
from xml.etree import ElementTree
import numpy as np
from .model import Signal


def load_bids(bids_path, *, modality="eeg", max_samples=20_000_000, max_metadata_bytes=1_000_000):
    """Read a local MNE-BIDS BIDSPath; preserve selected signal and sidecars.

    Dataset participant tables are not copied into exported signal metadata.
    Source recordings and demographics stay in the caller's dataset directory.
    """
    import mne_bids

    if not isinstance(bids_path, mne_bids.BIDSPath) or modality not in {"eeg", "emg", "ecg", "eog"}:
        raise ValueError("An explicit BIDSPath and electrical modality are required")
    sidecars = {}
    for suffix, extension in [
        (bids_path.datatype, ".json"),
        ("channels", ".tsv"),
        ("events", ".tsv"),
        ("electrodes", ".tsv"),
        ("coordsystem", ".json"),
    ]:
        if not suffix:
            continue
        path = bids_path.find_matching_sidecar(
            suffix=suffix, extension=extension, on_error="ignore"
        )
        if path is None:
            continue
        path = Path(path)
        if path.stat().st_size > max_metadata_bytes:
            raise ValueError("BIDS sidecar exceeds metadata limit")
        content = path.read_bytes()
        text = content.decode("utf-8-sig")
        parsed = (
            json.loads(text)
            if extension == ".json"
            else list(csv.DictReader(text.splitlines(), delimiter="\t"))
        )
        sidecars[suffix] = {
            "name": path.name,
            "sha256": hashlib.sha256(content).hexdigest(),
            "content": parsed,
        }
    raw = mne_bids.read_raw_bids(bids_path, verbose="ERROR")
    try:
        picks = [i for i, kind in enumerate(raw.get_channel_types()) if kind == modality]
        if not picks or raw.n_times * len(picks) > max_samples:
            raise ValueError("Requested BIDS modality is missing or exceeds sample limit")
        signal_json = sidecars.get(bids_path.datatype, {}).get("content", {})
        reference = signal_json.get("EEGReference") if modality == "eeg" else None
        metadata = {
            "format": "BIDS",
            "source": bids_path.basename,
            "mne_bids_version": mne_bids.__version__,
            "sidecars": sidecars,
            "bad_channels": list(raw.info["bads"]),
            "annotations": [
                {"onset_s": float(a), "duration_s": float(b), "description": str(c)}
                for a, b, c in zip(
                    raw.annotations.onset, raw.annotations.duration, raw.annotations.description
                )
            ],
            "unit_conversion": "MNE electrical volts explicitly converted to uV",
            "dataset_demographics": "not copied; remain in source BIDS dataset",
        }
        return Signal(
            raw.get_data(picks=picks) * 1e6,
            raw.info["sfreq"],
            tuple(raw.ch_names[i] for i in picks),
            modality,
            "uV",
            reference,
            metadata,
        )
    finally:
        raw.close()


def _varint(file):
    first = file.read(1)
    if len(first) != 1 or first[0] not in {1, 4, 8}:
        raise ValueError("Invalid XDF integer length")
    value = file.read(first[0])
    if len(value) != first[0]:
        raise ValueError("Truncated XDF integer")
    return int.from_bytes(value, "little")


def _preflight_xdf(path, stream_id, max_bytes):
    """Bound declared sample allocations before pyxdf's tolerant numeric parser."""
    size = path.stat().st_size
    if size > max_bytes or path.suffix.lower() != ".xdf":
        raise ValueError("Only bounded uncompressed .xdf files are accepted")
    formats = {"double64": 8, "float32": 4, "int32": 4, "int16": 2, "int8": 1, "int64": 8}
    count, channels, width = 0, None, None
    with path.open("rb") as file:
        if file.read(4) != b"XDF:":
            raise ValueError("Invalid XDF signature")
        while file.tell() < size:
            length = _varint(file)
            end = file.tell() + length
            if length < 2 or end > size:
                raise ValueError("Invalid XDF chunk extent")
            tag = int.from_bytes(file.read(2), "little")
            if tag in {1, 2, 6} and length > 1_000_000:
                raise ValueError("XDF metadata chunk exceeds limit")
            if tag in {2, 3, 4, 6}:
                if length < 6:
                    raise ValueError("Truncated XDF stream chunk")
                identity = int.from_bytes(file.read(4), "little")
                if identity == stream_id and tag == 2:
                    if channels is not None:
                        raise ValueError("Duplicate selected XDF stream header")
                    root = ElementTree.fromstring(file.read(end - file.tell()))
                    channels = int(root.findtext("channel_count", "0"))
                    width = formats.get(root.findtext("channel_format"))
                    if not 1 <= channels <= 16384 or width is None:
                        raise ValueError(
                            "Selected XDF stream must contain bounded numeric channels"
                        )
                elif identity == stream_id and tag == 3:
                    if channels is None:
                        raise ValueError("XDF samples precede selected stream header")
                    samples = _varint(file)
                    if samples * (1 + channels * width) > end - file.tell():
                        raise ValueError("XDF sample count exceeds chunk storage")
                    count += samples
                    if count * (8 * channels + 8) > max_bytes:
                        raise ValueError("XDF float64 sample allocation exceeds limit")
            file.seek(end)
    if channels is None or count < 2:
        raise ValueError("Selected XDF stream missing or contains fewer than two samples")
    return count, channels


def load_xdf(
    path,
    *,
    stream_id,
    modality,
    unit,
    reference=None,
    channels=None,
    timestamp_tolerance=0.05,
    max_bytes=256_000_000,
):
    """Select one regular numeric XDF stream; reject irregular/lost samples.

    Original timestamps are retained and never de-jittered or resampled. Clock
    synchronization is disabled so recorded stream timestamps remain unchanged.
    Multi-device clock synchronization and event-stream alignment need a separate
    scientifically specified workflow. Only uncompressed XDF is accepted.
    """
    import pyxdf

    if (
        isinstance(stream_id, bool)
        or not isinstance(stream_id, int)
        or not 0 <= stream_id <= 2**32 - 1
    ):
        raise ValueError("Explicit nonnegative integer XDF stream ID required")
    if not np.isfinite(timestamp_tolerance) or not 0 <= timestamp_tolerance <= 0.25:
        raise ValueError("Timestamp tolerance must be a relative interval fraction in [0,.25]")
    path = Path(path)
    count, channel_count = _preflight_xdf(path, stream_id, max_bytes)
    streams, header = pyxdf.load_xdf(
        path,
        select_streams=[stream_id],
        synchronize_clocks=False,
        handle_clock_resets=False,
        dejitter_timestamps=False,
        verbose=False,
    )
    if len(streams) != 1:
        raise ValueError("XDF selected stream is absent or ambiguous")
    stream = streams[0]
    data, timestamps = (
        np.asarray(stream["time_series"]),
        np.asarray(stream["time_stamps"], dtype=float),
    )
    if data.shape != (count, channel_count) or timestamps.shape != (count,):
        raise ValueError("XDF parser returned partial data; refuse tolerant corruption recovery")
    sfreq = float(stream["info"]["nominal_srate"][0])
    if not np.isfinite(sfreq) or sfreq <= 0 or not np.all(np.isfinite(timestamps)):
        raise ValueError("A positive nominal sample rate and finite timestamps are required")
    intervals = np.diff(timestamps)
    if np.any(intervals <= 0) or np.any(
        abs(intervals - 1 / sfreq) > max(1e-10, timestamp_tolerance / sfreq)
    ):
        raise ValueError(
            "Irregular XDF timestamps; explicit synchronization/resampling is required"
        )
    description = stream["info"].get("desc", [{}])[0]
    channel_info = (
        description.get("channels", [{}])[0].get("channel", [])
        if isinstance(description, dict)
        else []
    )
    labels = (
        tuple(channels)
        if channels is not None
        else tuple(entry.get("label", [""])[0] for entry in channel_info)
    )
    if len(labels) != channel_count:
        raise ValueError("Explicit channels or complete XDF channel labels are required")
    normalized_units = {
        "µV": "uV",
        "μV": "uV",
        "microvolts": "uV",
        "mV": "mV",
        "V": "V",
        "uV": "uV",
        "S": "S",
        "uS": "uS",
        "µS": "uS",
        "a.u.": "a.u.",
    }
    for entry in channel_info:
        declared = entry.get("unit", [""])[0]
        if declared and normalized_units.get(declared, declared) != unit:
            raise ValueError("Explicit unit disagrees with XDF channel unit; convert separately")
    metadata = {
        "format": "XDF",
        "source": path.name,
        "pyxdf_version": pyxdf.__version__,
        "stream_info": stream["info"],
        "file_header": header,
        "timestamps_s": timestamps.tolist(),
        "clock_times": np.asarray(stream["clock_times"]).tolist(),
        "clock_values": np.asarray(stream["clock_values"]).tolist(),
        "clock_policy": "recorded timestamps; no synchronization, reset correction, de-jittering or resampling",
    }
    return Signal(data.T, sfreq, labels, modality, unit, reference, metadata)
