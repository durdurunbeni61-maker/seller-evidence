# Seller Evidence

An offline Python CLI for independent digital-product sellers who want reliable
aggregate evidence before changing a product. Early-stage software, not a sales
prediction engine or a marketplace integration.

## What works today

- Strict CSV validation: schema, dates, counts, money, duplicate/overlapping
  snapshots, encoding, file size and row count.
- Reports that distinguish blank **UNKNOWN** from explicit **MEASURED zero**.
- Per-snapshot orders per visit, revenue per visit and average order value.
- Adjacent seven-day view-drop checks, configurable by threshold and baseline.
- Experiment previews, review dates and configurable freeze periods.
- Explicit local SQLite ledger writes, idempotent re-import and conflict rejection.

Python 3.12+; **zero third-party runtime dependencies**. No browser automation,
API clients, telemetry, account credentials or automatic publishing.

## Install from a source checkout

```sh
python -m venv .venv
# Linux/macOS
.venv/bin/python -m pip install .
# Windows PowerShell (use this instead on Windows)
.venv\Scripts\python.exe -m pip install .
```

The build backend is pinned in `pyproject.toml`. Installation may access your
package index for build tooling; the installed application does not use a network.
The examples below use `python` from the activated virtual environment. On Windows
activate with `.venv\Scripts\Activate.ps1`; on Linux/macOS use `source .venv/bin/activate`.
Alternatively use the full virtual-environment interpreter path without activation.

## Working example (all data is fictional)

```sh
python -m seller_evidence validate examples/stats.fictional.csv
python -m seller_evidence report examples/stats.fictional.csv
python -m seller_evidence experiments examples/experiments.fictional.csv --as-of 2030-01-28
python -m seller_evidence experiments examples/experiments.fictional.csv --as-of 2030-01-28 --commit --db data/demo.sqlite
```

Expected: 4 valid stats rows, one 40% weekly view-drop signal for `demo-A`,
measured zeros for `demo-B`, and unknown metrics for `demo-C`. The first ledger
write inserts 2 fictional experiments; repeating it inserts 0 and reports 2 unchanged.
Preview creates no database. Exit code 0 means success; 2 means invalid input or
local file operation. Errors do not echo submitted values or filesystem paths.

## Prepare your own input

The CSVs are **templates**, not universal marketplace export parsers. Map your
manually exported, authorized, aggregate data to [the documented schema](docs/SCHEMAS.md).
Use opaque local product IDs, one source definition per file, and exact documented
headers. Blank numeric cells mean missing measurement; type `0` only when measured.
Keep separate currencies, channels and periods separate. Do not submit customers,
orders, contact details or delivery contents. There is no listing/catalog importer.

```sh
python -m seller_evidence report data/stats.csv --drop-threshold 0.40 --minimum-views 100
python -m seller_evidence experiments data/experiments.csv --freeze-days 14
```

## Privacy and limitations

The CLI processes local files only. There is no data upload or external marketplace
access. The schema rejects unknown columns, but **does not anonymize cell contents**:
you must remove personal information before use. Free-text experiment fields and
opaque IDs can still contain private information. Local reports and SQLite files
are not encrypted, and `.gitignore` does not prevent deliberate disclosure.

Metrics are descriptive. Orders per visit is a ratio, not an official marketplace
conversion statistic. Ratios are undefined with a zero denominator. Comparisons
do not establish causality or correct seasonality, confounders, attribution or
measurement differences. A freeze is a planning status, not an enforcement lock.
A ledger record is not proof that a marketplace change was applied. The ledger
never overwrites an existing ID: use a new record ID when recording a later decision.
No predictive SEO, keyword demand, revenue guarantees, automatic experiment scoring,
marketplace policy certification or UI dashboard is implemented.

## Development

After installation, run:

```sh
python -m unittest discover -s tests -v
python scripts/check_release.py
```

The GitHub Actions workflow runs installation, examples, tests and a release-file
guard on push/PR with read-only permissions. It has been reviewed locally; a hosted
run is not claimed until this repository exists. See [CONTRIBUTING.md](CONTRIBUTING.md)
and [SECURITY.md](SECURITY.md).

## License and status

MIT; see [LICENSE](LICENSE) and [third-party notes](docs/THIRD_PARTY_NOTICES.md).
This is an early-stage release candidate. Public adoption, downloads, stars,
dependent projects and ecosystem impact have not been measured or established.
