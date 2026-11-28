# Live implementation checkpoint

This is a software implementation checkpoint, not a completed v0.6 or v1.0
release acceptance claim. Physical acquisition and independent verification
remain external gates.

| Component | Implemented behavior | Evidence and limits |
| --- | --- | --- |
| Simulator | Chunk-invariant seeded multichannel tones/noise, explicit units/sample clock, safe close | Synthetic source tests; not physiology |
| Buffer | Thread-safe bounded snapshots, sequence/timestamp gaps, separate source loss/window eviction counts | Concurrent reader/writer and overflow/gap tests |
| Processing | Causal normalized stable SOS, zero-state/reset lifecycle, warmup exclusion, real Welch PSD, exact-flat-channel controls | Continuous SciPy equality, known-tone peak/power, reset tests; no clinical quality claim |
| Recording | Numeric NPZ+JSON, original metadata, no overwrite, header/size/type limits, no pickle, raw-window checkpoint recovery | Roundtrip/playback/unsafe-archive tests; bounded contiguous runs only |
| Events | Locked bounded markers tied to exact retained sample timestamp/clock, explicit provenance and legacy recovery | Gap/eviction/replay/cancellation/concurrent-bound/clock-mismatch tests; no host event timing inference |
| Resources | Exact raw/processed ring array bytes; actual process RSS/peak with platform units | Real Linux observations and unsupported-platform null tests; RSS is whole process, not acquisition-only |
| Clock | Explicit affine calibration with RMS residual, guarded extrapolation | Analytical drift test; not a hardware accuracy bound |
| BrainFlow | Explicit started-board rows, source counters, close/ownership/error lifecycle | Native synthetic 16 channels at 250 Hz plus fakes; no physical board |
| LSL | Explicit resolution/metadata, optional clock correction, bounded read/disconnect lifecycle | Native same-host exact outlet roundtrip plus fakes; no multi-host timing claim |
| TCP/serial | Length-prefixed JSON custom protocol, partial reads and fail-closed limits | Real TCP loopback and pyserial virtual loop; no native board protocol |
| UDP/WebSocket | Bounded binary frames, explicit peer/TLS rules, malformed/oversize closure | Actual local loopback, UDP gap/reorder tests and WebSocket protocol-level rejection |
| Worker | Finite capture, bounded polling/status, explicit stop/idle limits, deliberate reconnect, owned-device cleanup | Completion, timeout, disconnect and blocked-native-read cancellation tests |
| Dashboard | Actual finite synthetic traces/spectra, gap simulation, optional paced rolling preview, raw contiguous export | Streamlit AppTest fast/gap/three-second animated runs |

At commit `4a86f3c`, branch verification ran `PYTHONPATH=$PWD/src python -m pytest tests -ra`:
**140 passed**, including all 107 original v0.3 tests and 33 Live tests. Critical
Ruff checks passed. Documentation links are checked separately; the exact count
changes when checkpoint documentation is added. These are local Linux results,
not remote CI or a cross-platform verification claim. The subsequent events,
resources and recovery update adds six meaningful Live tests. Current focused
verification is `python -m pytest tests/live -ra`: **39 passed**, with critical
Ruff and documentation link checks passing. The parent integration owns
final combined regression/security/package/browser checks.

Current measured [CPU benchmark](benchmark-expanded-streaming-results.json)
and [native adapter results](native-adapter-expanded-results.json) contain source
hashes and actual dependency/host versions. Initial
[CPU](benchmark-results.json) and [native](native-adapter-results.json) reports
remain preserved. The CPU benchmark has a real maximum-latency outlier; do not
replace it with a nominal deadline or omit it. Tracemalloc is Python allocator
peak, not process RSS. No fabricated end-to-end performance figures are supplied.
The subsequent [event/resource/recovery report](session-event-resource-results.json)
records a new source snapshot: two exact 12,000-byte rings, actual whole-process
Linux RSS observations, events at retained samples 750 and 999, and a successful
500-sample raw-window replay preserving full event provenance. Kernel RSS
interfaces are distinct observations; discrepancies are preserved, not tuned.

Commits before this final validation/refinement: `b2a83d5` (core/dashboard),
`051c599` (optional adapters), `7215a9d` (network gateways/worker), `4a86f3c`
(paced capture and strict serialization). The next action is parent
integration/review of the events/resources/recovery commit and a combined suite with
the Engine/AI/Studio workstreams. Root-level release checklists own milestone
acceptance; this checkpoint does not advance version numbers.

Remaining acceptance work: physical OpenBCI/ADS1299 or other board selection and
electrical/timing validation; long-duration multi-host LSL/network dropout and
clock uncertainty studies; protocol-specific USB/serial device adapters;
authenticated deployment of custom transports; end-to-end device/display latency
and process-RSS/resource studies; real user evaluation and independent review.
No such work has been claimed as complete.
