"""Actual synthetic XDF/BIDS files exercise parsers, metadata and failure cases."""

import json
from pathlib import Path
import struct
import numpy as np
import pytest
from biosignal_lab.engine import load_xdf, load_bids


def _vint(n):
    return bytes([4]) + struct.pack("<I", n)


def _chunk(tag, data):
    content = struct.pack("<H", tag) + data
    return _vint(len(content)) + content


def write_xdf(path, *, count=100, gap=False, unit="uV", declared_count=None):
    info = (
        f"<info><name>Synthetic</name><type>EEG</type><channel_count>2</channel_count>"
        f"<nominal_srate>100</nominal_srate><channel_format>float32</channel_format>"
        f"<desc><channels><channel><label>A</label><unit>{unit}</unit></channel>"
        f"<channel><label>B</label><unit>{unit}</unit></channel></channels></desc></info>"
    )
    samples = b"".join(
        b"\x08"
        + struct.pack(
            "<dff", 100 + i / 100 + (0.1 if gap and i >= 50 else 0), float(i), float(2 * i)
        )
        for i in range(count)
    )
    path.write_bytes(
        b"XDF:"
        + _chunk(1, b"<info><version>1.0</version></info>")
        + _chunk(2, struct.pack("<I", 42) + info.encode())
        + _chunk(
            3,
            struct.pack("<I", 42)
            + _vint(count if declared_count is None else declared_count)
            + samples,
        )
    )


def test_actual_xdf_data_timestamps_labels_and_units_are_preserved(tmp_path):
    pytest.importorskip("pyxdf")
    path = tmp_path / "synthetic.xdf"
    write_xdf(path)
    signal = load_xdf(path, stream_id=42, modality="eeg", unit="uV", reference="synthetic_zero")
    np.testing.assert_array_equal(signal.data[0], np.arange(100))
    np.testing.assert_array_equal(signal.data[1], 2 * np.arange(100))
    assert signal.channels == ("A", "B") and signal.sfreq == 100 and signal.unit == "uV"
    np.testing.assert_allclose(signal.metadata["timestamps_s"], 100 + np.arange(100) / 100)
    assert signal.metadata["stream_info"]["name"] == ["Synthetic"]
    assert signal.metadata["file_header"]["info"]["version"] == ["1.0"]
    with pytest.raises(ValueError, match="unit disagrees"):
        load_xdf(path, stream_id=42, modality="eeg", unit="V")


def test_xdf_discontinuity_and_declared_sample_allocation_fail_closed(tmp_path):
    pytest.importorskip("pyxdf")
    path = tmp_path / "gap.xdf"
    write_xdf(path, gap=True)
    with pytest.raises(ValueError, match="Irregular"):
        load_xdf(path, stream_id=42, modality="eeg", unit="uV")
    attack = tmp_path / "oversized-count.xdf"
    write_xdf(attack, declared_count=2**31)
    with pytest.raises(ValueError, match="sample count exceeds"):
        load_xdf(attack, stream_id=42, modality="eeg", unit="uV")
    with pytest.raises(ValueError, match="missing"):
        load_xdf(path, stream_id=99, modality="eeg", unit="uV")


def write_bids_edf(root):
    target = root / "sub-01" / "eeg"
    target.mkdir(parents=True)
    base = target / "sub-01_task-synthetic_eeg"
    labels, fs, count = ["Fz", "Cz"], 100, 4
    fields = [
        ("0", 8),
        ("synthetic fixture", 80),
        ("synthetic fixture", 80),
        ("01.01.24", 8),
        ("01.01.01", 8),
        ("768", 8),
        ("", 44),
        (str(count), 8),
        ("1", 8),
        ("2", 4),
    ]
    header = "".join(value.ljust(width)[:width] for value, width in fields)
    for width, values in [
        (16, labels),
        (80, ["none"] * 2),
        (8, ["uV"] * 2),
        (8, ["-1000"] * 2),
        (8, ["1000"] * 2),
        (8, ["-32768"] * 2),
        (8, ["32767"] * 2),
        (80, ["none"] * 2),
        (8, [str(fs)] * 2),
        (32, [""] * 2),
    ]:
        header += "".join(value.ljust(width)[:width] for value in values)
    with base.with_suffix(".edf").open("wb") as output:
        output.write(header.encode())
        for _ in range(count):
            output.write(np.full(fs, 100, dtype="<i2").tobytes())
            output.write(np.full(fs, 200, dtype="<i2").tobytes())
    base.with_suffix(".json").write_text(
        json.dumps(
            {
                "TaskName": "synthetic",
                "SamplingFrequency": 100,
                "EEGReference": "synthetic_zero",
                "PowerLineFrequency": 50,
                "SoftwareFilters": "n/a",
                "EEGChannelCount": 2,
                "RecordingDuration": 4,
                "RecordingType": "continuous",
            }
        )
    )
    (target / "sub-01_task-synthetic_channels.tsv").write_text(
        "name\ttype\tunits\tstatus\nFz\tEEG\tuV\tgood\nCz\tEEG\tuV\tbad\n"
    )
    (target / "sub-01_task-synthetic_events.tsv").write_text(
        "onset\tduration\ttrial_type\tvalue\tsample\n1\t0.5\tsynthetic_event\t1\t100\n"
    )
    (root / "dataset_description.json").write_text(
        json.dumps({"Name": "Synthetic adapter test", "BIDSVersion": "1.9.0", "DatasetType": "raw"})
    )
    return base


def test_actual_bids_edf_sidecars_reference_annotations_and_units(tmp_path):
    mne_bids = pytest.importorskip("mne_bids")
    root = tmp_path / "bids"
    write_bids_edf(root)
    path = mne_bids.BIDSPath(
        root=root, subject="01", task="synthetic", datatype="eeg", suffix="eeg", extension=".edf"
    )
    signal = load_bids(path)
    assert signal.channels == ("Fz", "Cz") and signal.reference == "synthetic_zero"
    assert signal.data.shape == (2, 400) and signal.unit == "uV" and signal.sfreq == 100
    expected = (np.array([100, 200]) + 32768) * (2000 / 65535) - 1000
    np.testing.assert_allclose(signal.data[:, 100], expected, rtol=1e-8)
    assert signal.metadata["bad_channels"] == ["Cz"]
    assert signal.metadata["sidecars"]["events"]["content"][0]["trial_type"] == "synthetic_event"
    assert any(item["description"] == "synthetic_event" for item in signal.metadata["annotations"])
    assert signal.metadata["sidecars"]["eeg"]["sha256"]
    with pytest.raises(ValueError, match="metadata limit"):
        load_bids(path, max_metadata_bytes=10)
    with pytest.raises(ValueError, match="sample limit"):
        load_bids(path, max_samples=10)


@pytest.mark.parametrize("extension", ["bdf", "BDF"])
def test_actual_24bit_bdf_modality_and_amplitude_scaling(tmp_path, extension):
    pytest.importorskip("mne")
    from biosignal_lab.engine import load_mne

    fs, records, labels = 100, 3, ["EEG Fz", "EMG Chin"]
    fields = [
        ("synthetic fixture", 80),
        ("synthetic fixture", 80),
        ("01.01.24", 8),
        ("01.01.01", 8),
        ("768", 8),
        ("24BIT", 44),
        (str(records), 8),
        ("1", 8),
        ("2", 4),
    ]
    # BioSemi's BDF variant has the EDF header layout with this exact version
    # signature and little-endian signed24-bit samples (not EDF's16-bit samples).
    header = b"\xffBIOSEMI" + "".join(value.ljust(width)[:width] for value, width in fields).encode(
        "ascii"
    )
    for width, values in [
        (16, labels),
        (80, ["none"] * 2),
        (8, ["uV"] * 2),
        (8, ["-1000"] * 2),
        (8, ["1000"] * 2),
        (8, ["-8388608"] * 2),
        (8, ["8388607"] * 2),
        (80, ["none"] * 2),
        (8, [str(fs)] * 2),
        (32, [""] * 2),
    ]:
        header += "".join(value.ljust(width)[:width] for value in values).encode("ascii")
    assert len(header) == 768
    time = np.arange(fs * records) / fs
    amplitude = np.array([20 * np.sin(2 * np.pi * 10 * time), 200 * np.sin(2 * np.pi * 40 * time)])
    digital = np.rint((amplitude + 1000) * (16777215 / 2000) - 8388608).astype(np.int32)
    path = tmp_path / f"synthetic.{extension}"
    with path.open("wb") as output:
        output.write(header)
        for record in range(records):
            for channel in range(2):
                selected = digital[channel, record * fs : (record + 1) * fs]
                encoded = ((selected[:, None] >> np.array([0, 8, 16])) & 255).astype(np.uint8)
                output.write(encoded.tobytes())
    eeg = load_mne(path, modality="eeg")
    emg = load_mne(path, modality="emg")
    assert eeg.channels == ("Fz",) and emg.channels == ("Chin",)
    assert eeg.sfreq == emg.sfreq == fs and eeg.unit == emg.unit == "uV"
    expected = (digital.astype(float) + 8388608) * (2000 / 16777215) - 1000
    np.testing.assert_allclose(eeg.data[0], expected[0], atol=1e-10)
    np.testing.assert_allclose(emg.data[0], expected[1], atol=1e-10)
    assert eeg.metadata["format"] == "bdf"
