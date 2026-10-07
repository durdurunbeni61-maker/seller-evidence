"""Fictional regression tests for data integrity, scope and storage behavior."""

import contextlib
import csv
import io
import json
import sqlite3
import shutil
import unittest
import uuid
from datetime import date
from pathlib import Path

from seller_evidence.analysis import AnalysisConfig, metric, ratio, summarize, weekly_drops
from seller_evidence.cli import main
from seller_evidence.csv_data import EXPERIMENT_COLUMNS, STATS_COLUMNS, ValidationError, load_stats, read_table
from seller_evidence.experiments import experiment_status, load_experiments, store_experiments


def observation(**changes):
    row = dict(zip(STATS_COLUMNS, ("demo-A", "2030-01-07", "2030-01-13", "search", "100", "20", "2", "30.00", "USD")))
    row.update(changes)
    return row


def experiment(**changes):
    row = dict(zip(EXPERIMENT_COLUMNS, ("demo-exp-A", "demo-A", "2030-01-07", "cover", "Original layout", "Larger headline", "Clearer cover increases relevant clicks", "Unchanged demo-B cover", "2030-01-28", "", "")))
    row.update(changes)
    return row


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        # Ordinary test directories also work in restricted Windows environments.
        self.test_parent = Path(__file__).resolve().parent / ".test-tmp"
        self.root = self.test_parent / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.addCleanup(self.cleanup_directory)

    def cleanup_directory(self):
        if self.root.resolve().parent != self.test_parent.resolve():
            raise RuntimeError("Refusing cleanup outside the test directory")
        shutil.rmtree(self.root)

    def table(self, rows, columns=STATS_COLUMNS, delimiter=",", encoding="utf-8"):
        path = self.root / "fictional.csv"
        with path.open("w", newline="", encoding=encoding) as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, delimiter=delimiter)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_missing_and_measured_zero_are_different(self):
        rows = load_stats(self.table([observation(visits="0", orders="", revenue="0.00")]))
        report = summarize(rows)[0]
        self.assertEqual(report["metrics"]["visits"], {"value": 0, "status": "MEASURED"})
        self.assertEqual(report["metrics"]["orders"]["status"], "UNKNOWN")
        self.assertEqual(report["revenue_per_visit"]["status"], "UNDEFINED")

    def test_decimal_money_survives_exactly(self):
        row = load_stats(self.table([observation(revenue="0.10")]))[0]
        self.assertEqual(row["revenue"], "0.10")
        self.assertEqual(ratio("0.10", 2)["value"], "0.050000")

    def test_zero_orders_with_positive_visits_is_measured(self):
        self.assertEqual(ratio(0, 10), {"value": "0.000000", "status": "MEASURED"})

    def test_blank_ratios_remain_unknown(self):
        self.assertEqual(ratio(None, 10)["status"], "UNKNOWN")
        self.assertEqual(ratio(10, None)["status"], "UNKNOWN")
        self.assertEqual(metric(None)["status"], "UNKNOWN")

    def test_utf8_bom_utf16_and_delimiters(self):
        for encoding in ("utf-8-sig", "utf-16"):
            for delimiter in (",", ";", "\t"):
                with self.subTest(encoding=encoding, delimiter=delimiter):
                    self.assertEqual(len(load_stats(self.table([observation()], delimiter=delimiter, encoding=encoding))), 1)

    def test_unknown_and_personal_columns_rejected(self):
        for column in ("email", "date_of_birth", "customer", "extra"):
            with self.subTest(column=column), self.assertRaises(ValidationError):
                load_stats(self.table([dict(observation(), **{column: "fictional"})], (*STATS_COLUMNS, column)))

    def test_duplicate_headers_rejected(self):
        path = self.root / "fictional.csv"
        path.write_text(",".join((*STATS_COLUMNS, "visits")) + "\n", encoding="utf-8")
        with self.assertRaises(ValidationError):
            load_stats(path)

    def test_invalid_counts_rejected(self):
        for value in ("-1", "1.5", "NaN", "True", "１"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                load_stats(self.table([observation(visits=value)]))

    def test_invalid_money_rejected(self):
        for value in ("NaN", "Infinity", "-1", "1,20", "1e3"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                load_stats(self.table([observation(revenue=value)]))

    def test_dates_currency_identifier_rejected(self):
        for changes in ({"period_start": "20300107"}, {"period_end": "2030-01-06"},
                        {"currency": "usd"}, {"product_id": "private/customer"}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                load_stats(self.table([observation(**changes)]))

    def test_overlapping_and_duplicate_snapshots_rejected(self):
        for other in (observation(), observation(period_start="2030-01-10", period_end="2030-01-16")):
            with self.subTest(other=other), self.assertRaises(ValidationError):
                load_stats(self.table([observation(), other]))

    def test_scopes_are_not_summed(self):
        rows = load_stats(self.table([observation(), observation(channel="social"), observation(currency="EUR")]))
        self.assertEqual(len(summarize(rows)), 3)

    def test_malformed_column_count(self):
        path = self.table([observation()])
        path.write_text(path.read_text() + "extra,columns\n", encoding="utf-8")
        with self.assertRaises(ValidationError):
            load_stats(path)

    def test_empty_and_header_only_rejected(self):
        for text in ("", ",".join(STATS_COLUMNS) + "\n"):
            path = self.root / "empty.csv"
            path.write_text(text, encoding="utf-8")
            with self.subTest(text=text), self.assertRaises(ValidationError):
                load_stats(path)

    def test_bounded_read_and_row_limit(self):
        path = self.table([observation()])
        with self.assertRaises(ValidationError):
            read_table(path, STATS_COLUMNS, max_bytes=10)
        with self.assertRaises(ValidationError):
            read_table(path, STATS_COLUMNS, max_rows=0)

    def test_control_characters_not_allowed(self):
        with self.assertRaises(ValidationError):
            load_stats(self.table([observation(channel="search\x00")]))

    def weekly_rows(self, **second_changes):
        return load_stats(self.table([observation(), observation(period_start="2030-01-14", period_end="2030-01-20", views="60", **second_changes)]))

    def test_adjacent_week_drop(self):
        drops = weekly_drops(self.weekly_rows(), AnalysisConfig())
        self.assertEqual(len(drops), 1)
        self.assertEqual(drops[0]["views_drop_fraction"], 0.4)

    def test_threshold_and_baseline_configurable(self):
        self.assertEqual(weekly_drops(self.weekly_rows(), AnalysisConfig(0.5, 50)), [])
        self.assertEqual(weekly_drops(self.weekly_rows(), AnalysisConfig(0.3, 101)), [])

    def test_nonadjacent_or_mixed_scope_not_compared(self):
        for changes in ({"channel": "social"}, {"currency": "EUR"},
                        {"period_start": "2030-01-21", "period_end": "2030-01-27"}):
            rows = load_stats(self.table([observation(), observation(views="60", **changes)]))
            self.assertEqual(weekly_drops(rows, AnalysisConfig()), [])

    def test_unknown_baseline_no_alert(self):
        rows = load_stats(self.table([observation(views=""), observation(period_start="2030-01-14", period_end="2030-01-20", views="0")]))
        self.assertEqual(weekly_drops(rows, AnalysisConfig()), [])

    def test_incomplete_week_not_compared(self):
        rows = load_stats(self.table([observation(), observation(period_start="2030-01-14", period_end="2030-01-18", views="0")]))
        self.assertEqual(weekly_drops(rows, AnalysisConfig()), [])

    def test_invalid_config_rejected(self):
        for threshold in (0, -1, 2, float("nan"), float("inf")):
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                AnalysisConfig(threshold)

    def test_experiment_preview_and_freeze(self):
        rows = load_experiments(self.table([experiment()], EXPERIMENT_COLUMNS), freeze_days=14)
        status = experiment_status(rows, date(2030, 1, 20))[0]
        self.assertTrue(status["frozen"])
        self.assertEqual(status["result_status"], "UNKNOWN")
        self.assertFalse((self.root / "data.sqlite").exists())

    def test_experiment_due_date(self):
        rows = load_experiments(self.table([experiment()], EXPERIMENT_COLUMNS))
        self.assertTrue(experiment_status(rows, date(2030, 1, 28))[0]["review_due"])

    def test_experiment_invalid_decision_dates_control(self):
        for changes in ({"decision": "WIN"}, {"decision_on": "2030-01-01"},
                        {"decision": "KEEP"}, {"control": ""}, {"new_value": "Original layout"}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                load_experiments(self.table([experiment(**changes)], EXPERIMENT_COLUMNS))

    def test_experiment_idempotence_and_conflict_rollback(self):
        rows = load_experiments(self.table([experiment()], EXPERIMENT_COLUMNS))
        database = self.root / "local.sqlite"
        self.assertEqual(store_experiments(rows, database), {"inserted": 1, "unchanged": 0})
        self.assertEqual(store_experiments(rows, database), {"inserted": 0, "unchanged": 1})
        changed = dict(rows[0], new_value="Different layout")
        new = dict(rows[0], experiment_id="demo-exp-B")
        with self.assertRaises(ValidationError):
            store_experiments([new, changed], database)
        with contextlib.closing(sqlite3.connect(database)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM experiments").fetchone()[0], 1)

    def test_duplicate_experiment_batch_rejected(self):
        with self.assertRaises(ValidationError):
            load_experiments(self.table([experiment(), experiment()], EXPERIMENT_COLUMNS))

    def test_cli_report_and_validate(self):
        path = self.table([observation()])
        for command in ("validate", "report"):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main([command, str(path)]), 0)
            self.assertEqual(json.loads(output.getvalue())["valid_rows"], 1)

    def test_cli_errors_do_not_echo_input_path_or_values(self):
        path = self.table([observation(visits="not-a-number")])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["validate", str(path)]), 2)
        self.assertNotIn(str(path), output.getvalue())
        self.assertNotIn("not-a-number", output.getvalue())

    def test_cli_requires_explicit_database_to_commit(self):
        path = self.table([experiment()], EXPERIMENT_COLUMNS)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["experiments", str(path), "--commit"]), 2)
        self.assertEqual(list(self.root.glob("*.sqlite")), [])

    def test_cli_preview_commit_and_repeat(self):
        path = self.table([experiment()], EXPERIMENT_COLUMNS)
        database = self.root / "ledger.sqlite"
        for commit in (False, True, True):
            output = io.StringIO()
            args = ["experiments", str(path), "--as-of", "2030-01-28"]
            if commit:
                args += ["--commit", "--db", str(database)]
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(args), 0)
            self.assertEqual(json.loads(output.getvalue())["committed"], commit)


if __name__ == "__main__":
    unittest.main()
