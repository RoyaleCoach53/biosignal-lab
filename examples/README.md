# Examples and sample datasets

Both committed CSV files are **synthetic, MIT licensed, and contain no human data**.
They are educational textures, not validated physiological recordings.

| File | Modality | Sampling | Duration | Channels |
| --- | --- | --- | --- | --- |
| [eeg_demo.csv](data/eeg_demo.csv) | EEG-like | 250 Hz | 10 s | Ch1, Ch2 |
| [emg_demo.csv](data/emg_demo.csv) | EMG-like | 2000 Hz | 5 s | Ch1 |

The `time_s` column is seconds; signal columns are microvolts. The EEG example
contains known tones, noise, and a synthetic amplitude transient near 5 seconds.
The EMG example contains envelope-modulated noise. The simulator's `with_artifacts`
flag currently adds the explicit transient to EEG only.

## Regenerate

From the repository root after installing the package:

```sh
python examples/generate_samples.py
```

The generator uses seed 42, writes bounded-precision CSV files, and records
SHA-256 checksums, units, and settings in [manifest.json](data/manifest.json).
For exact byte comparison, use the recorded dependency environment; platform
floating-point differences may affect final decimal places.

## Analyze and inspect

```sh
biosignal-lab analyze --input examples/data/eeg_demo.csv --sfreq 250 --time-column time_s --output local-results/eeg
biosignal-lab analyze --input examples/data/emg_demo.csv --sfreq 2000 --modality emg --time-column time_s --output local-results/emg
```

Open the resulting HTML reports locally. For interactive inspection run
`streamlit run app.py`, select **Upload CSV / EDF**, upload a sample, enter its
sampling rate and `uv` units, and set the time column to `time_s`.
[config.json](config.json) is an example of the Python `AnalysisConfig` fields;
the CLI does not currently load JSON config files directly.

Do not add private or restricted recordings. Any future human dataset needs
documented provenance, consent/access conditions, and redistribution rights.
