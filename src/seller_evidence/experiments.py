"""Validated local experiment ledger with configurable review freeze."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import timedelta
from pathlib import Path

from .csv_data import EXPERIMENT_COLUMNS, ValidationError, identifier, iso_date, read_table

DECISIONS = {"", "KEEP", "REVERT", "RETEST", "EXPAND"}


def load_experiments(path: Path, *, freeze_days: int = 21) -> list[dict]:
    """Validate a complete batch before creating or updating a database."""
    if type(freeze_days) is not int or not 0 <= freeze_days <= 365:
        raise ValidationError("Freeze days must be an integer in [0, 365]")
    rows = read_table(path, EXPERIMENT_COLUMNS)
    seen = set()
    result = []
    for number, row in enumerate(rows, 2):
        try:
            identifier(row["experiment_id"])
            identifier(row["product_id"])
            identifier(row["variable"])
            if row["experiment_id"] in seen:
                raise ValidationError("Duplicate experiment identifier")
            seen.add(row["experiment_id"])
            started, review = iso_date(row["started_on"]), iso_date(row["decision_on"])
            if review < started:
                raise ValidationError("Decision date precedes start")
            if row["decision"] not in DECISIONS:
                raise ValidationError("Unsupported decision")
            if not row["hypothesis"] or not row["control"]:
                raise ValidationError("Hypothesis and control are required")
            if row["old_value"] == row["new_value"]:
                raise ValidationError("Old and new value must differ")
            if row["decision"] and not row["result"]:
                raise ValidationError("A decision requires a recorded result")
            if any(len(value) > 4000 for value in row.values()):
                raise ValidationError("Experiment field exceeds length limit")
            item = dict(row)
            item["freeze_until"] = (started + timedelta(days=freeze_days)).isoformat()
            result.append(item)
        except (ValidationError, OverflowError) as exc:
            raise ValidationError(f"Row {number}: invalid experiment ({exc})") from exc
    return result


def store_experiments(rows: list[dict], database: Path) -> dict:
    """Atomically insert validated records; reject changed IDs instead of hiding conflicts."""
    database.parent.mkdir(parents=True, exist_ok=True)
    columns = (*EXPERIMENT_COLUMNS, "freeze_until")
    inserted = unchanged = 0
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS experiments (
            experiment_id TEXT PRIMARY KEY, product_id TEXT NOT NULL,
            started_on TEXT NOT NULL, variable TEXT NOT NULL, old_value TEXT NOT NULL,
            new_value TEXT NOT NULL, hypothesis TEXT NOT NULL, control TEXT NOT NULL,
            decision_on TEXT NOT NULL, decision TEXT NOT NULL, result TEXT NOT NULL,
            freeze_until TEXT NOT NULL)""")
        for row in rows:
            payload = tuple(row[name] for name in columns)
            old = connection.execute("SELECT * FROM experiments WHERE experiment_id = ?",
                                     (row["experiment_id"],)).fetchone()
            if old is not None:
                if old != payload:
                    raise ValidationError("Existing experiment ID conflicts; use a new record ID")
                unchanged += 1
            else:
                connection.execute("INSERT INTO experiments VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", payload)
                inserted += 1
    return {"inserted": inserted, "unchanged": unchanged}


def experiment_status(rows: list[dict], as_of) -> list[dict]:
    """Show freeze and decision status; never claim a tracked change was applied."""
    results = []
    for row in rows:
        frozen = as_of < iso_date(row["freeze_until"])
        due = not row["decision"] and as_of >= iso_date(row["decision_on"])
        results.append({"experiment_id": row["experiment_id"], "product_id": row["product_id"],
                        "frozen": frozen, "review_due": due,
                        "decision": row["decision"] or None,
                        "result": row["result"] or None,
                        "result_status": "RECORDED" if row["result"] else "UNKNOWN"})
    return results
