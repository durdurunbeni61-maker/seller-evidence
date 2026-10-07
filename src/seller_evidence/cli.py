"""Command-line interface that only reads and writes local files."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date
from pathlib import Path

from .analysis import AnalysisConfig, summarize, weekly_drops
from .csv_data import ValidationError, iso_date, load_stats
from .experiments import experiment_status, load_experiments, store_experiments


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate an aggregate stats CSV")
    validate.add_argument("file", type=Path)
    report = commands.add_parser("report", help="Report metrics and comparable-week view drops")
    report.add_argument("file", type=Path)
    report.add_argument("--drop-threshold", type=float, default=0.30)
    report.add_argument("--minimum-views", type=int, default=50)
    experiment = commands.add_parser("experiments", help="Preview or explicitly save an experiment batch")
    experiment.add_argument("file", type=Path)
    experiment.add_argument("--freeze-days", type=int, default=21)
    experiment.add_argument("--as-of", type=iso_date, default=date.today())
    experiment.add_argument("--commit", action="store_true")
    experiment.add_argument("--db", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "experiments":
            rows = load_experiments(args.file, freeze_days=args.freeze_days)
            result = {"valid_rows": len(rows), "committed": False,
                      "experiments": experiment_status(rows, args.as_of)}
            if args.commit:
                if args.db is None:
                    raise ValidationError("Commit requires an explicit local database path")
                result.update(store_experiments(rows, args.db))
                result["committed"] = True
        else:
            rows = load_stats(args.file)
            result = {"valid_rows": len(rows)}
            if args.command == "report":
                config = AnalysisConfig(args.drop_threshold, args.minimum_views)
                result.update({"snapshots": summarize(rows), "weekly_view_drops": weekly_drops(rows, config)})
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except ValidationError as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
        return 2
    except (OSError, ValueError, sqlite3.Error):
        # Keep paths and submitted content out of diagnostic output.
        print(json.dumps({"status": "error", "reason": "Invalid input or local file operation; no submitted values logged"}))
        return 2
