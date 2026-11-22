# Examples and sample data

The original examples and datasets have not yet been recovered. This directory
currently documents the requirements for safe, reproducible examples; it does
not contain an executable application tutorial or a sample recording.

The first verified example should:

1. Generate a deterministic synthetic signal with explicit units and sampling rate.
2. Show the actual installation and application commands from a clean checkout.
3. Export the selected settings, result, and source commit.
4. Compare a numerical measurement with a stated analytical target and tolerance.
5. Explain what the result can and cannot mean scientifically.

Each committed dataset needs a provenance note, license, column or channel
description, sampling information, duration, units, and checksum. Synthetic data
must be labeled synthetic. Human data requires appropriate permission and
redistribution rights; do not add identifiable or restricted recordings.

Use small data files suitable for ordinary cloning. Link to larger public
datasets under their own access and license terms instead of silently vendoring them.
