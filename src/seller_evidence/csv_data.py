"""Validate a deliberately narrow, aggregate-only CSV format."""

from __future__ import annotations

import csv
import io
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

STATS_COLUMNS = (
    "product_id", "period_start", "period_end", "channel", "views",
    "visits", "orders", "revenue", "currency",
)
EXPERIMENT_COLUMNS = (
    "experiment_id", "product_id", "started_on", "variable", "old_value",
    "new_value", "hypothesis", "control", "decision_on", "decision", "result",
)
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


class ValidationError(ValueError):
    """A structural error that does not include submitted values or file paths."""


def read_table(path: Path, columns: tuple[str, ...], *, max_bytes: int = 5_000_000,
               max_rows: int = 100_000) -> list[dict[str, str]]:
    """Read UTF-8/BOM or UTF-16 CSV; reject unexpected and personal columns."""
    with path.open("rb") as stream:
        raw = stream.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValidationError("Input exceeds size limit")
    try:
        encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
        text = raw.decode(encoding)
        header = text.splitlines()[0]
        delimiter = csv.Sniffer().sniff(header, delimiters=",;\t").delimiter
        reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter,
                                doublequote=True, strict=True)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or set(headers) != set(columns):
            raise ValidationError("Columns must match the documented schema exactly")
        rows = []
        for number, row in enumerate(reader, 2):
            if len(rows) >= max_rows:
                raise ValidationError("Input exceeds row limit")
            if None in row or any(value is None for value in row.values()):
                raise ValidationError(f"Row {number}: malformed column count")
            item = {key: value.strip() for key, value in row.items()}
            if any(any(ord(char) < 32 for char in value) for value in item.values()):
                raise ValidationError(f"Row {number}: control characters are not allowed")
            rows.append(item)
        if not rows:
            raise ValidationError("At least one data row is required")
        return rows
    except (UnicodeError, IndexError, csv.Error) as exc:
        raise ValidationError("Invalid CSV encoding or syntax") from exc


def iso_date(value: str) -> date:
    """Require a canonical calendar date rather than silently guessing locale."""
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError
        return parsed
    except ValueError as exc:
        raise ValidationError("Expected date in YYYY-MM-DD format") from exc


def count(value: str) -> int | None:
    """Blank is unknown; an explicit zero is a measured zero."""
    if not value:
        return None
    if not re.fullmatch(r"[0-9]+", value):
        raise ValidationError("Counts must be non-negative integers or blank")
    return int(value)


def money(value: str) -> str | None:
    """Keep finite, non-negative decimal money as text, never binary float."""
    if not value:
        return None
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
        raise ValidationError("Money must use non-negative decimal notation or blank")
    return format(Decimal(value), "f")


def identifier(value: str) -> str:
    """Use opaque local identifiers, not names or customer/order identifiers."""
    if not IDENTIFIER.fullmatch(value):
        raise ValidationError("Expected an opaque alphanumeric identifier")
    return value


def load_stats(path: Path) -> list[dict]:
    """Validate all rows before returning any observations."""
    rows = read_table(path, STATS_COLUMNS)
    observations: list[dict] = []
    periods: dict[tuple, list[tuple[date, date, int]]] = {}
    for number, row in enumerate(rows, 2):
        try:
            identifier(row["product_id"])
            identifier(row["channel"])
            start, end = iso_date(row["period_start"]), iso_date(row["period_end"])
            if start > end:
                raise ValidationError("Period start must not follow end")
            if not re.fullmatch(r"[A-Z]{3}", row["currency"]):
                raise ValidationError("Currency must be an explicit three-letter code")
            item = dict(row)
            for key in ("views", "visits", "orders"):
                item[key] = count(row[key])
            item["revenue"] = money(row["revenue"])
            key = (row["product_id"], row["channel"], row["currency"])
            periods.setdefault(key, []).append((start, end, number))
            observations.append(item)
        except ValidationError as exc:
            raise ValidationError(f"Row {number}: {exc}") from exc
    for intervals in periods.values():
        intervals.sort()
        for previous, current in zip(intervals, intervals[1:]):
            if current[0] <= previous[1]:
                raise ValidationError(f"Row {current[2]}: duplicate or overlapping snapshot in the same scope")
    return observations
