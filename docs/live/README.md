# BioSignal Live: verified simulated research acquisition

The Live package provides finite acquisition building blocks and a local
Streamlit workbench. It has been tested with a deterministic simulator and a
custom TCP protocol over loopback. No physical board, USB, OpenBCI, ADS1299,
BrainFlow or LSL integration has been verified or is advertised as supported.
Serial, UDP and WebSocket acquisition remain future adapter work.

Start from the repository root after installing `.[dev,all]`:

```sh
streamlit run live_app.py
python -m pytest tests/live -ra
python benchmarks/live/streaming.py --output local-results/live-benchmark.json
```

The benchmark refuses existing output paths. Use a new name on retries to retain
earlier evidence. The dashboard captures a finite virtual-clock stream without
sleeping or creating background acquisition threads. Changing controls does not
alter an already captured result until **Capture synthetic stream** is pressed.
Select the dropped-block control to exercise sequence-gap detection and filter
reset. Export contains only the contiguous raw run retained after the gap;
the diagnostics retain the dropped-sample count.

## SDK and data contracts

```python
from biosignal_lab.live import StreamInfo, SimulatedDevice, LiveProcessor
from scipy.signal import butter

info = StreamInfo(250, ("C3", "C4"), ("uV", "uV"), clock="simulated_seconds")
source = SimulatedDevice(info, seed=42)
processor = LiveProcessor(info, butter(4, [1, 40], btype="bandpass", fs=250,
                                     output="sos"), window_s=2, warmup_s=1)
for _ in range(20):
    result = processor.process(source.read(50))
source.close()
assert result.psd is not None
```

`StreamInfo` requires a finite positive sampling frequency, unique channel names,
one explicit unit per channel, modality and clock identifier. This API does not
convert units implicitly. Mixed-unit streams remain explicit; a caller must not
interpret every channel's power as uV²/Hz. `SampleBlock` stores a defensive,
read-only float64 copy with channels × samples, one strictly increasing finite
timestamp per sample, and a nonnegative integer `start_sample`. Timestamps are
seconds in the declared clock, not assumed UTC. Empty blocks are not accepted.
The simulator output is chunk-invariant for a fixed seed, frequency and channel
configuration, and is not a physiological truth model.

`RingBuffer(capacity, n_channels, sfreq)` uses a lock around append, snapshot and
diagnostics. Snapshot is a defensive copy. It retains at most the configured
sample capacity. `overwritten_samples` measures old retained samples displaced
by new samples; it is normal sliding-window eviction, not source data loss.
`dropped_samples` counts gaps in source sequence indices. `discontinuities`
also counts timestamp gaps. Timestamp intervals must agree with the nominal
sampling frequency within 5%; this tolerance is a configurable-protocol limit
currently fixed in the implementation, not a metrological specification.
On a discontinuity, the buffer discards the previous contiguous window rather
than joining samples across a gap. Duplicate and overlapping sequence indices,
backwards timestamps, wrong channel counts and malformed rates raise errors.

`LiveProcessor` supports stable, normalized SOS filters from SciPy. State starts
at zero and persists across blocks; a discontinuity resets filter state and the
PSD window. There is no forward/backward filtering, future information, padding,
or automatic delay compensation. `warmup_s` excludes samples from spectral
monitoring but does not guarantee filter settling. Choose an exclusion using
the actual filter's impulse response. A PSD appears only when a complete
post-exclusion contiguous window exists. Welch uses a Hann window, one segment,
constant detrending and density scaling; the result is input-unit²/Hz. The
reported processing duration excludes acquisition, network and display latency.
Flat-channel flags are exact-constant controls, not clinical signal-quality
decisions.

## Recording and playback

`save_recording(path, info, block, markers)` writes a new file exclusively and
preserves any existing path, including symlinks. Markers contain an in-range
integer `sample` and a 1–256 character `label`. Data stay in native units and
device timestamps. NPZ archives contain numeric arrays and a JSON metadata
scalar; loading disables pickle, checks archive member names and uncompressed
sizes, validates NPY array headers before allocation, limits recording values
(default ten million), and revalidates all metadata and markers. This is bounded
local file parsing, not a guarantee against all malicious archive variants.
`recording_bytes` supports in-memory exports without disk files.

`PlaybackDevice(path).read(n)` returns up to the requested number of samples and
raises `EOFError` at the end. It preserves original sequence numbers and timestamps
and does not replay in wall-clock time. Readers should call `close()` explicitly.

## Clock calibration and transport

`ClockAlignment.fit(device_times, host_times)` fits scale and offset from at
least three paired increasing measurements and reports residual RMS. Transform
refuses extrapolation outside the observed interval unless explicitly allowed.
Calibration residual is not an upper bound on network jitter or clock error,
and this method does not synchronize an uncalibrated device automatically.

`TCPDevice(socket, info, timeout=2, max_bytes=1048576)` is an explicit custom
gateway protocol. Each frame has a four-byte unsigned network-order payload
length followed by UTF-8 JSON with exactly `data`, `timestamps`, `start_sample`.
Use `encode_frame(block)` to generate it. The stream metadata are supplied
out-of-band by the caller and must match the physical source. Reads handle
partial frames, enforce a byte/sample limit, and close the connection on a
malformed frame, timeout or disconnection. There is no automatic reconnect;
create a new device and a fresh processor session deliberately. The adapter is
plaintext, unauthenticated and intended only for trusted local networks or a
caller-managed authenticated encrypted connection. It is not an OpenBCI protocol.

## Acceptance evidence and remaining gates

Tests compare chunked causal filtering against a single continuous SciPy call,
check known-tone frequency and integrated spectral power, exercise gap resets,
overflow, out-of-order blocks, concurrent snapshots, clock calibration, safe
recording/playback, malicious archive rejection, fragmented TCP loopback frames,
oversized-frame shutdown and the actual dashboard capture/export flow.

The benchmark records host CPU, architecture, Python/NumPy/SciPy versions,
sample rate, channel/block counts, CPU timing percentiles and Python allocator
peak. It is synthetic throughput evidence. Tracemalloc does not measure process
RSS or every native allocation. Container scheduling affects timing and there
are no real-time deadline guarantees. Physical acquisition, packet-loss detection
against hardware sequence counters, reconnect stability, hardware timestamp
accuracy, end-to-end latency and human usability remain incomplete gates.
