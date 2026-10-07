"""Descriptive metrics and comparable-week checks, not causal inference."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from math import isfinite


@dataclass(frozen=True)
class AnalysisConfig:
    """Generic thresholds; there are no shop-specific seasonal assumptions."""

    drop_threshold: float = 0.30
    minimum_previous_views: int = 50

    def __post_init__(self) -> None:
        if not isfinite(self.drop_threshold) or not 0 < self.drop_threshold <= 1:
            raise ValueError("Drop threshold must be finite and in (0, 1]")
        if type(self.minimum_previous_views) is not int or self.minimum_previous_views < 1:
            raise ValueError("Minimum previous views must be a positive integer")


def metric(value: int | str | None) -> dict:
    """Serialize unknown explicitly; never substitute zero for missing data."""
    return {"value": value, "status": "UNKNOWN" if value is None else "MEASURED"}


def ratio(numerator: int | str | None, denominator: int | None) -> dict:
    """A zero denominator is undefined, even when the numerator is zero."""
    if numerator is None or denominator is None:
        return {"value": None, "status": "UNKNOWN", "reason": "Missing measurement"}
    if denominator == 0:
        return {"value": None, "status": "UNDEFINED", "reason": "Zero denominator"}
    return {"value": format(Decimal(str(numerator)) / Decimal(denominator), ".6f"),
            "status": "MEASURED"}


def summarize(rows: list[dict]) -> list[dict]:
    """Keep product, period, channel and currency separate; do not sum overlaps."""
    output = []
    for row in rows:
        item = {key: row[key] for key in
                ("product_id", "period_start", "period_end", "channel", "currency")}
        item["metrics"] = {key: metric(row[key]) for key in ("views", "visits", "orders", "revenue")}
        item["orders_per_visit"] = ratio(row["orders"], row["visits"])
        item["revenue_per_visit"] = ratio(row["revenue"], row["visits"])
        item["average_order_value"] = ratio(row["revenue"], row["orders"])
        output.append(item)
    return output


def weekly_drops(rows: list[dict], config: AnalysisConfig) -> list[dict]:
    """Compare adjacent seven-day snapshots only within an identical scope."""
    scopes: dict[tuple, list[dict]] = {}
    for row in rows:
        start, end = date.fromisoformat(row["period_start"]), date.fromisoformat(row["period_end"])
        if end - start == timedelta(days=6):
            key = tuple(row[name] for name in ("product_id", "channel", "currency"))
            scopes.setdefault(key, []).append(row)
    results = []
    for key, snapshots in scopes.items():
        snapshots.sort(key=lambda row: row["period_start"])
        for previous, current in zip(snapshots, snapshots[1:]):
            if date.fromisoformat(current["period_start"]) - date.fromisoformat(previous["period_start"]) != timedelta(days=7):
                continue
            before, after = previous["views"], current["views"]
            if before is None or after is None or before < config.minimum_previous_views:
                continue
            fraction = (before - after) / before
            if fraction >= config.drop_threshold:
                results.append({"product_id": key[0], "channel": key[1], "currency": key[2],
                                "previous_start": previous["period_start"],
                                "current_start": current["period_start"],
                                "views_drop_fraction": fraction,
                                "interpretation": "Descriptive signal; cause and seasonality are unverified"})
    return results
