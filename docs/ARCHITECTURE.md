# Architecture review

The package uses a small, inspectable pipeline rather than a network service.

```text
CSV / EDF or simulator
        |
    Recording + AnalysisConfig
        |
    gap validation / mean removal / offline filters
        |
    PSD + metrics + band powers + raw-signal quality candidates
        |
    AnalysisResults
        |
    Python API / CLI exports / Streamlit dashboard
```

## Responsibilities

- `models.py`: recording shape, units, modality, sampling rate, and configuration validation.
- `io.py`: numeric CSV conversion and timestamp checks; optional MNE EDF input.
- `preprocessing.py`: bounded interpolation, mean removal, notch, and Butterworth filters.
- `analysis.py`: descriptive spectral/time-domain metrics and candidate heuristics.
- `pipeline.py`: modality-specific defaults and explicit interpretation warnings.
- `report.py`: strict JSON (`allow_nan=False`) and escaped self-contained HTML.
- `cli.py`: local input handling and exports; `app.py`: interactive local UI.
- `simulate.py`: deterministic educational fixtures; no human physiology claim.

## Review conclusions and boundaries

I/O, processing, reporting, and presentation are separate enough for focused tests.
Configuration travels with exported summaries, and no credentials or external API
calls are required by application analysis code. HTML escapes untrusted labels.
The release review found and corrected defects documented in the changelog.

The implementation is in-memory and intended for modest recordings. CSV import
has no streaming engine or core API size limit; the dashboard caps upload size.
The frozen `Recording` dataclass does not make its NumPy array deeply immutable;
callers should avoid concurrent mutation. EDF type inference depends on labels.
Tests cover synthetic examples, not every file variant, acquisition system, or
numeric overflow case. These are explicit limits, not guarantees of security or
physiological validity.
