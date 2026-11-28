"""Actual process memory observations with explicit scope and platform units."""
from pathlib import Path
import os
import platform
from time import monotonic


def process_memory_usage() -> dict:
    """Observe this entire Python process, not isolated acquisition allocations.

    Linux current RSS comes from /proc/self/statm (resident pages × page size).
    resource.getrusage peak RSS uses KiB on Linux and bytes on macOS. Other
    platforms report unavailable rather than guessing units. No optional package
    or new background sampler is needed.
    """
    current = peak = None
    current_source = peak_source = None
    if platform.system() == "Linux":
        try:
            pages = int(Path("/proc/self/statm").read_text().split()[1])
            current = pages * os.sysconf("SC_PAGE_SIZE")
            current_source = "Linux procfs resident pages times OS page size"
        except (OSError, ValueError, IndexError):
            pass
    if platform.system() in ("Linux", "Darwin"):
        try:
            import resource
            native_peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            peak = int(native_peak * (1024 if platform.system() == "Linux" else 1))
            peak_source = "resource.RUSAGE_SELF.ru_maxrss; Linux KiB converted to bytes" if platform.system() == "Linux" else "resource.RUSAGE_SELF.ru_maxrss; macOS bytes"
        except (ImportError, OSError, ValueError):
            pass
    return {"process_rss_bytes": current, "process_peak_rss_bytes": peak,
            "current_rss_source": current_source, "peak_rss_source": peak_source,
            "scope": "Entire current Python process including other modules, threads and native libraries; not acquisition-only",
            "host_monotonic_measurement_s": monotonic(),
            "clock_note": "Host monotonic observation time; no equivalence to device sample clock implied",
            "unavailable_values": "null means unavailable; not zero memory usage"}
