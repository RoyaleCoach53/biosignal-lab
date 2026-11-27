# Development integration compatibility

The integration is not a published v1.0 release. Existing imports of `Recording`,
`AnalysisConfig`, `analyze`, legacy analysis reports, and EEG/EMG demo commands
remain supported. Historical measurements retain their original version labels.

One intentional safety change affects output paths: CLI reports and synthetic
CSV demos refuse existing destinations by default. Use a new path for every
scientific run. Only the CLI supports explicit `--overwrite` when replacement is
intended. Benchmark, tutorial and clean-install audit evidence require new paths;
they do not offer a silent overwrite option. This prevents old optional tables
or reports from being mistaken for current-run results.

Use `engine.Signal` for new modalities or non-voltage units. `Recording.data_uv`
has not changed semantics. Transformation history records filtering direction,
padding and resampling assumptions; algorithms with different edge policies
must not be compared as if they were identical.

New entrypoints:

```sh
python -m streamlit run platform_app.py
biosignal-lab --version
biosignal-lab workflow --help
biosignal-lab ai --help
```

The source dashboard and website remain source-distribution/repository workflows.
A Python wheel installs the library and CLI, not a standalone desktop application.
JSON workflow/model schemas are versioned and unknown schemas fail explicitly.
Experimental new subsystem APIs can evolve before stable acceptance; save exact
source commits and dependency versions with experiments.
