"""Explicitly synthetic AI experiment command line."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from .demo import synthetic_epoch_dataset, synthetic_feature_dataset
from .learning import evaluate_grouped, train_linear
from .portable import save_linear_model
from .neural import save_temporal_model, train_temporal


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Evaluate synthetic 10 Hz/20 Hz tones; no physiological task claim")
    demo.add_argument("--output", type=Path, required=True, help="New experiment directory; never overwrites existing work")
    demo.add_argument("--model", choices=["lda", "logistic"], default="lda")
    demo.add_argument("--seed", type=int, default=42)
    demo.add_argument("--subjects", type=int, default=8)
    neural = commands.add_parser("neural-demo", help="Train a CPU network on synthetic spatial variance patterns")
    neural.add_argument("--output", type=Path, required=True, help="New experiment directory")
    neural.add_argument("--architecture", choices=["temporal_conv1d_v1", "eegnet_v1"], default="temporal_conv1d_v1")
    neural.add_argument("--max-epochs", type=int, default=25)
    neural.add_argument("--seed", type=int, default=42)
    neural.add_argument("--subjects", type=int, default=8)
    args = parser.parse_args(argv)
    created = False
    try:
        args.output.mkdir(parents=True, exist_ok=False)
        created = True
        if args.command == "demo":
            dataset = synthetic_feature_dataset(seed=args.seed, n_subjects=args.subjects)
            report = evaluate_grouped(dataset, model=args.model, seed=args.seed)
            report["data_scope"] = "Synthetic 10 Hz and 20 Hz tones only; no physiological or clinical accuracy claim."
            model = train_linear(dataset, args.model, args.seed)
        else:
            dataset = synthetic_epoch_dataset(seed=args.seed, n_subjects=args.subjects)
            model, report = train_temporal(dataset, seed=args.seed, architecture=args.architecture,
                                           max_epochs=args.max_epochs)
            report["data_scope"] = "Synthetic spatial variance only; no physiological or clinical accuracy claim."
        with (args.output / "evaluation.json").open("x", encoding="utf-8") as output:
            output.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
        if args.command == "demo":
            save_linear_model(model, args.output / "model.json")
        else:
            save_temporal_model(model, args.output / "model.json")
    except (ValueError, OSError, ImportError, RuntimeError) as exc:
        if created:
            shutil.rmtree(args.output)
        parser.exit(1, f"Synthetic AI experiment failed: {exc}\n")
    if args.command == "demo":
        count, accuracy = report["n_subjects"], report["metrics"]["accuracy"]
    else:
        count, accuracy = len(report["test_subjects"]), report["test_metrics"]["accuracy"]
    print(f"Synthetic classification: {count} held-out simulated subjects; "
          f"accuracy {accuracy:.3f}. No physiological task validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
