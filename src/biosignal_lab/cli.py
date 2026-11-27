"""Command-line entry point: demos, batch QC and export."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import pandas as pd
from .models import AnalysisConfig
from .simulate import synthetic_recording
from .io import read_csv, read_edf
from .pipeline import analyze, default_config
from .report import json_report, html_report
from ._version import __version__


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="biosignal-lab", description="Local EEG/EMG research QC")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("workflow", add_help=False, help="Validate, run or generate Python for a Studio workflow")
    sub.add_parser("ai", add_help=False, help="Reproducible synthetic grouped-learning demonstration")
    demo = sub.add_parser("demo", help="Generate deterministic example CSV with artifact")
    demo.add_argument("--output", default="sample_eeg.csv")
    demo.add_argument("--modality", choices=["eeg", "emg"], default="eeg")
    demo.add_argument("--duration", type=float, default=30)
    demo.add_argument("--sfreq", type=float, default=250)
    demo.add_argument("--channels", type=int, default=8)
    demo.add_argument("--overwrite", action="store_true", help="Replace an existing synthetic CSV")
    analysis = sub.add_parser("analyze", help="Analyze one local CSV or EDF recording")
    analysis.add_argument("--input", required=True)
    analysis.add_argument("--output", default="results")
    analysis.add_argument("--sfreq", type=float, help="Required for CSV; Hz")
    analysis.add_argument("--unit", choices=["uv", "mv", "v"], default="uv")
    analysis.add_argument("--time-column", help="Optional CSV time column to exclude")
    analysis.add_argument("--modality", choices=["eeg", "emg"], default="eeg")
    analysis.add_argument("--highpass", type=float, default=None)
    analysis.add_argument("--lowpass", type=float, default=None)
    analysis.add_argument("--notch", type=float, default=None)
    analysis.add_argument("--no-notch", action="store_true")
    analysis.add_argument("--window", type=float, default=None)
    analysis.add_argument("--artifact-window", type=float, default=1.0)
    analysis.add_argument("--overwrite", action="store_true", help="Replace reports at this output prefix")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["workflow"]:
        from .studio.cli import main as workflow_main
        return workflow_main(argv[1:])
    if argv[:1] == ["ai"]:
        from .ai.cli import main as ai_main
        return ai_main(argv[1:])
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "demo":
        rec = synthetic_recording(duration_s=args.duration, sfreq=args.sfreq,
                                  n_channels=args.channels, modality=args.modality)
        frame = pd.DataFrame(rec.data_uv.T, columns=rec.channels)
        frame.insert(0, "time_s", [i / rec.sfreq for i in range(frame.shape[0])])
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.is_symlink():
            parser.error("Refusing a symbolic-link output")
        try:
            frame.to_csv(output, index=False, mode="w" if args.overwrite else "x")
        except FileExistsError:
            parser.error("Output exists; choose a new path or explicitly use --overwrite")
        print(f"Wrote {output} ({len(rec.channels)} channels, {rec.duration_s:g}s, values µV)")
        return 0
    path = Path(args.input)
    if not path.is_file():
        parser.error(f"Input does not exist: {path}")
    if path.suffix.lower() == ".csv":
        if args.sfreq is None:
            parser.error("--sfreq is required for CSV input")
        rec = read_csv(path, sfreq=args.sfreq, modality=args.modality,
                       unit=args.unit, time_column=args.time_column)
    elif path.suffix.lower() == ".edf":
        rec = read_edf(path, modality=args.modality)
    else:
        parser.error("Supported input formats: .csv, .edf")
    default_window = min(4. if args.modality == "eeg" else 2., rec.duration_s)
    window = args.window if args.window is not None else default_window
    defaults = default_config(args.modality, rec.sfreq, window_s=window)
    hp = args.highpass if args.highpass is not None else defaults.highpass_hz
    lp = args.lowpass if args.lowpass is not None else defaults.lowpass_hz
    notch = None if args.no_notch else (args.notch if args.notch is not None else defaults.notch_hz)
    config = AnalysisConfig(modality=args.modality, highpass_hz=hp, lowpass_hz=lp,
                            notch_hz=notch, window_s=window, artifact_window_s=args.artifact_window)
    result = analyze(rec, config)
    base = Path(args.output)
    base.parent.mkdir(parents=True, exist_ok=True)
    # Reserve every possible report name so stale optional tables cannot masquerade
    # as outputs from the current analysis.
    targets = [Path(str(base) + suffix) for suffix in
               (".json", ".html", "_quality.csv", "_bands.csv", "_artifacts.csv")]
    if any(p.resolve() == path.resolve() for p in targets):
        parser.error("An output report cannot replace the input recording")
    if any(p.is_symlink() for p in targets):
        parser.error("Refusing a symbolic-link output")
    if not args.overwrite and any(p.exists() for p in targets):
        parser.error("Report prefix already exists; choose a new prefix or explicitly use --overwrite")
    contents = {targets[0]: json_report(result), targets[1]: html_report(result),
                targets[2]: pd.DataFrame(result.channel_metrics).to_csv(index=False)}
    if result.band_powers:
        contents[targets[3]] = pd.DataFrame(result.band_powers).to_csv(index=False)
    if result.artifact_intervals:
        contents[targets[4]] = pd.DataFrame(result.artifact_intervals).to_csv(index=False)
    created = []
    try:
        for target, text in contents.items():
            with target.open("w" if args.overwrite else "x", encoding="utf-8", newline="") as stream:
                created.append(target)
                stream.write(text)
    except OSError:
        if not args.overwrite:
            for target in created:
                target.unlink(missing_ok=True)
        parser.error("Report export failed; choose a writable, unused output prefix")
    if args.overwrite:
        for target in targets:
            if target not in contents and target.exists():
                target.unlink()
    print(f"Analyzed {len(rec.channels)} channels over {rec.duration_s:.1f}s")
    print(f"Artifact review candidates: {len(result.artifact_intervals)}")
    print(f"Wrote {base}.json, {base}.html and quality CSV")
    for warn in result.warnings:
        print(f"WARNING: {warn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
