# Input schemas

All files in `examples/` are entirely fictional. The dates, IDs, counts, money
and experiment descriptions were invented for tests; they are not shop observations.

## Aggregate stats

Exact headers (order may differ): `product_id,period_start,period_end,channel,views,visits,orders,revenue,currency`.

| Field | Required value |
|---|---|
| product_id | Opaque local ID: ASCII letters/digits, underscore or hyphen, 1–64 characters |
| period_start / period_end | Ordered inclusive YYYY-MM-DD dates |
| channel | Opaque channel label in the same ID format |
| views / visits / orders | Non-negative integer, or blank for unknown |
| revenue | Non-negative decimal-point notation, or blank; preserved as decimal text |
| currency | Three uppercase ASCII letters; explicitly choose your actual currency |

Comma, semicolon and tab delimiters; UTF-8, UTF-8 BOM and UTF-16 BOM supported.
Unknown/duplicate headers, malformed rows and control characters are rejected.
Inclusive periods must not overlap for the same product, channel and currency.
The CLI uses a 5 MB / 100,000 row limit. There is no locale/currency conversion.
Use one measurement source definition per file. Do not combine different platforms'
definitions of a visit. Seven-day intervals are assumed complete based on their dates;
the software cannot verify that all measurements were collected.

## Experiments

Exact headers: `experiment_id,product_id,started_on,variable,old_value,new_value,hypothesis,control,decision_on,decision,result`.

IDs and `variable` use the opaque ID format. Start/review dates use YYYY-MM-DD;
review cannot precede start. Old and new values must differ. A hypothesis and
control description are required. Other text is capped at 4,000 characters per
field. `decision` is blank, KEEP, REVERT, RETEST or EXPAND. A non-blank decision
requires a result note; the software does not validate that note's truth.

Freeze days are configurable from 0 to 365, default 21. Records should concern
one variable; the schema stores this but cannot verify a real-world experiment.
SQLite imports validate the full CSV first. Identical IDs/content are unchanged;
different content under an existing ID rejects the transaction. Later decisions
can be recorded as a new ID with a result note referring to the earlier local ID.
Do not use customer, transaction or order IDs as product/experiment identifiers.
