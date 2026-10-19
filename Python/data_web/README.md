# data_web — 22 standalone Python data utilities

Small, complete, single-file programs covering CSV/JSON processing, SQLite,
HTTP clients and servers, scraping, backups, scheduling and reporting.

**Dependencies: none.** Standard library only, Python 3.10+, Windows-safe.
Every network tool has an offline mode (`--demo`, `--offline`, `--file` or
`--once`), so the whole collection can be exercised without internet access.

## Programs

| File | What it does |
|---|---|
| `csv_cleaner.py` | Stream-clean a CSV: trim, dedupe, drop empty rows, fill blanks, lowercase columns. |
| `json_store.py` | Persistent JSON key/value store with dotted keys and atomic writes. |
| `sqlite_crud.py` | Inventory CRUD CLI on SQLite with validation and `--dry-run`. |
| `sqlite_query_runner.py` | Run read-only SQL against a SQLite file; table/CSV/JSON output. |
| `expense_tracker.py` | Record expenses and budgets, produce monthly category reports and CSV exports. |
| `portfolio_tracker.py` | Track holdings, FIFO sales, valuation and allocation from a local price file. |
| `weather_cli.py` | Current conditions and 5-day forecast from Open-Meteo with retries; offline demo. |
| `http_client.py` | urllib HTTP client with methods, headers, JSON/form bodies, retries and backoff. |
| `rest_api_server.py` | Threaded JSON CRUD task API with validation, status codes and a self-test mode. |
| `static_file_server.py` | Safe static file server with directory listings and traversal guards. |
| `web_scraper.py` | Polite urllib + html.parser scraper with robots checks and offline HTML parsing. |
| `rss_reader.py` | RSS 2.0 / Atom reader with keyword filtering, table and JSON output. |
| `contact_book.py` | SQLite contact manager with tags, search and vCard export. |
| `backup_tool.py` | SHA-256 snapshot backups with verify, restore, zip archives and listing. |
| `download_manager.py` | Concurrent downloads with Range resume, retries and checksum verification. |
| `task_scheduler.py` | Run interval jobs from a JSON config, with logging, `--once` and `--dry-run`. |
| `system_report.py` | OS, CPU, memory, disk and Python details as text or JSON. |
| `disk_usage_report.py` | Directory size report: largest folders/files, extension breakdown, bars. |
| `svg_chart.py` | Render CSV columns as a standalone SVG bar or line chart. |
| `report_generator.py` | Build a self-contained HTML or Markdown summary report from CSV/JSON. |
| `data_pipeline.py` | Streaming read → transform → aggregate → write pipeline with sample generator. |
| `log_rotator.py` | Size-based log rotation, optional gzip, archive listing and age/count pruning. |

## Quick start

```powershell
# CSV cleaning
python csv_cleaner.py messy.csv -o clean.csv --trim --dedupe --drop-empty

# JSON store
python json_store.py --file store.json set app.port 8080
python json_store.py --file store.json get app.port

# SQLite
python sqlite_crud.py --db stock.db init
python sqlite_crud.py --db stock.db add Widget tools 12 4.50 --notes "bin A"
python sqlite_query_runner.py stock.db "SELECT category, SUM(quantity) FROM items GROUP BY category"

# Money
python expense_tracker.py --db money.db add 2026-10-18 food 24.50 --note lunch
python expense_tracker.py --db money.db report --month 2026-10
python portfolio_tracker.py --db portfolio.db buy AAPL 10 150 --prices prices.json

# Network tools (no internet needed)
python weather_cli.py --demo
python http_client.py --demo
python web_scraper.py --demo
python rss_reader.py --demo
python download_manager.py --demo

# Servers (each self-tests and exits)
python rest_api_server.py --once
python static_file_server.py --once

# Live server on localhost:8000
python rest_api_server.py --port 8000 --db tasks.db
python static_file_server.py ./public --port 8000

# Backup / automation
python backup_tool.py backup ./project --dest ./backups --zip
python backup_tool.py verify ./backups/project_20261019_120000
python task_scheduler.py --config jobs.json --once
python log_rotator.py rotate app.log --max-bytes 5MB --keep 5 --gzip

# Reporting
python system_report.py --json
python disk_usage_report.py . --top 15
python svg_chart.py sales.csv --x month --y revenue --out revenue.svg
python report_generator.py sales.csv --title "Q3 Sales" --out report.html
python data_pipeline.py --generate-sample 20000 --out sample.csv
python data_pipeline.py --input sample.csv --group-by region --value amount --agg sum --out totals.csv
```

## Conventions

- Mutating tools support `--dry-run`; most refuse to overwrite existing files
  unless `--force` is passed.
- All file I/O uses explicit UTF-8 encoding; CSV writers use explicit newlines.
- SQLite statements are always parameterised, and connections use a
  commit/rollback/close context manager.
- Network calls use short timeouts and a small retry loop with backoff; the
  programs never block indefinitely and print actionable errors.
- Every file has a module docstring, type hints, and an
  `if __name__ == "__main__":` entry point.
