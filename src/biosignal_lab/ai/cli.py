"""Explicitly synthetic AI experiment command line."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from .demo import synthetic_feature_dataset
from .learning import evaluate_grouped, train_linear
from .portable import save_linear_model


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Evaluate synthetic 10 Hz/20 Hz tones; no physiological task claim")
    demo.add_argument("--output", type=Path, required=True, help="New experiment directory; never overwrites existing work")
    demo.add_argument("--model", choices=["lda", "logistic"], default="lda")
    demo.add_argument("--seed", type=int, default=42)
    demo.add_argument("--subjects", type=int, default=8)
    args = parser.parse_args(argv)
    created = False
    try:
        args.output.mkdir(parents=True, exist_ok=False)
        created = True
        dataset = synthetic_feature_dataset(seed=args.seed, n_subjects=args.subjects)
        report = evaluate_grouped(dataset, model=args.model, seed=args.seed)
        report["data_scope"] = "Synthetic 10 Hz and 20 Hz tones only; no physiological or clinical accuracy claim."
        model = train_linear(dataset, args.model, args.seed)
        with (args.output / "evaluation.json").open("x", encoding="utf-8") as output:
            output.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
        save_linear_model(model, args.output / "model.json")
    except (ValueError, OSError, ImportError, RuntimeError) as exc:
        if created:
            shutil.rmtree(args.output)
        parser.exit(1, f"Synthetic AI experiment failed: {exc}\n")
    print(f"Synthetic tone classification: {report['n_subjects']} held-out simulated subjects; "
          f"accuracy {report['metrics']['accuracy']:.3f}. No physiological task validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
