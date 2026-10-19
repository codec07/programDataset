"""Run ad-hoc read-only SQL against a SQLite database and format the results.

Safety: only statements beginning with SELECT, WITH, EXPLAIN, PRAGMA or VALUES
are accepted; the connection is opened in read-only URI mode so a mistake
cannot modify the file.  Results are streamed into a table, CSV or JSON.

Usage:
    python sqlite_query_runner.py sales.db "SELECT * FROM orders LIMIT 5"
    python sqlite_query_runner.py sales.db --file query.sql --format json
    python sqlite_query_runner.py sales.db "SELECT * FROM orders WHERE id = :id" \
        --param id=3
    python sqlite_query_runner.py --demo
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

ALLOWED = ("select", "with", "explain", "pragma", "values")
PARAM_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.DOTALL)


def split_statements(text: str) -> list[str]:
    """Split on semicolons outside string literals and comments."""
    statements: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    i = 0
    while i < len(text):
        ch = text[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                if i + 1 < len(text) and text[i + 1] == quote:
                    buf.append(text[i + 1])
                    i += 2
                    continue
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            buf.append(ch)
        elif ch == "-" and text.startswith("--", i):
            end = text.find("\n", i)
            end = len(text) if end == -1 else end
            buf.append(" ")
            i = end
            continue
        elif ch == ";":
            if "".join(buf).strip():
                statements.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    if "".join(buf).strip():
        statements.append("".join(buf).strip())
    return statements


def is_read_only(sql: str) -> bool:
    stripped = sql.lstrip()
    first = stripped.split(None, 1)[0].lower() if stripped else ""
    return first in ALLOWED


def parse_params(pairs: Sequence[str]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for pair in pairs:
        match = PARAM_RE.match(pair)
        if not match:
            raise ValueError(f"bad --param {pair!r}; expected name=value")
        name, raw = match.groups()
        if raw.lower() in ("true", "false"):
            params[name] = raw.lower() == "true"
        elif raw.lower() in ("null", "none"):
            params[name] = None
        else:
            try:
                params[name] = int(raw)
            except ValueError:
                try:
                    params[name] = float(raw)
                except ValueError:
                    params[name] = raw
    return params


def connect_readonly(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def run_query(conn: sqlite3.Connection, sql: str, params: dict[str, Any],
              limit: int) -> tuple[list[str], list[tuple[Any, ...]]]:
    cur = conn.execute(sql, params)
    columns = [d[0] for d in (cur.description or [])]
    rows = cur.fetchmany(limit)
    return columns, [tuple(r) for r in rows]


def render_table(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    if not columns:
        return "(no result set)"

    def fmt(value: Any) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bytes):
            return f"<{len(value)} bytes>"
        return str(value)

    widths = [len(c) for c in columns]
    body = [[fmt(v) for v in row] for row in rows]
    for row in body:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))
    widths = [min(w, 40) for w in widths]

    def line(cells: list[str]) -> str:
        return "  ".join(c[:widths[i]].ljust(widths[i]) for i, c in enumerate(cells))

    out = [line(columns), "  ".join("-" * w for w in widths)]
    out.extend(line(row) for row in body)
    out.append(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")
    return "\n".join(out)


def render_csv(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return buf.getvalue().rstrip("\n")


def render_json(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    records = [dict(zip(columns, row)) for row in rows]
    return json.dumps(records, indent=2, default=str, ensure_ascii=False)


def execute_text(db: Path, text: str, params: dict[str, Any], limit: int,
                 fmt: str) -> int:
    statements = split_statements(text)
    if not statements:
        print("error: empty query", file=sys.stderr)
        return 2
    conn = connect_readonly(db)
    try:
        for sql in statements:
            if not is_read_only(sql):
                print(f"error: refused non-read-only statement: {sql[:60]}",
                      file=sys.stderr)
                return 2
            columns, rows = run_query(conn, sql, params, limit)
            if fmt == "csv":
                print(render_csv(columns, rows))
            elif fmt == "json":
                print(render_json(columns, rows))
            else:
                print(render_table(columns, rows))
    finally:
        conn.close()
    return 0


def demo() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "demo.db"
        conn = sqlite3.connect(db)
        try:
            conn.executescript(
                """
                CREATE TABLE orders (id INTEGER PRIMARY KEY, item TEXT, qty INTEGER,
                                     price REAL);
                INSERT INTO orders (item, qty, price) VALUES
                    ('widget', 4, 2.50), ('gadget', 1, 19.99), ('widget', 2, 2.50);
                """
            )
            conn.commit()
        finally:
            conn.close()
        print("-- table --")
        execute_text(db, "SELECT item, SUM(qty) AS units, "
                         "ROUND(SUM(qty * price), 2) AS total "
                         "FROM orders GROUP BY item ORDER BY total DESC", {}, 20, "table")
        print("\n-- json with parameter --")
        execute_text(db, "SELECT * FROM orders WHERE item = :item", {"item": "widget"},
                     20, "json")
        print("\n-- refused statement --")
        execute_text(db, "DELETE FROM orders", {}, 20, "table")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Read-only SQLite query runner.")
    p.add_argument("db", nargs="?", type=Path, help="SQLite database file")
    p.add_argument("sql", nargs="?", help="SQL text (read-only statements only)")
    p.add_argument("--file", type=Path, help="read SQL from a .sql file")
    p.add_argument("--param", action="append", default=[], metavar="NAME=VALUE",
                   help="bind a named parameter (repeatable)")
    p.add_argument("--format", choices=("table", "csv", "json"), default="table")
    p.add_argument("--limit", type=int, default=100, help="max rows per statement")
    p.add_argument("--demo", action="store_true", help="run an offline demonstration")
    args = p.parse_args(argv)

    if args.demo:
        return demo()
    if not args.db or not args.db.is_file():
        print("error: database file not found", file=sys.stderr)
        return 2
    if args.file:
        try:
            text = args.file.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    elif args.sql:
        text = args.sql
    else:
        print("error: provide SQL text or --file", file=sys.stderr)
        return 2

    try:
        params = parse_params(args.param)
        return execute_text(args.db, text, params, max(1, args.limit), args.format)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except sqlite3.Error as exc:
        print(f"sql error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
