"""Personal expense tracker with SQLite storage and monthly reports.

Records expenses (date, category, amount, note) and produces per-category
monthly reports, budget comparisons and CSV exports.  All SQL is
parameterised and writes run inside a transaction context manager.

Usage:
    python expense_tracker.py --db money.db add 2026-10-18 food 24.50 --note lunch
    python expense_tracker.py --db money.db list --month 2026-10
    python expense_tracker.py --db money.db budget food 300
    python expense_tracker.py --db money.db report --month 2026-10
    python expense_tracker.py --db money.db export expenses.csv --month 2026-10
    python expense_tracker.py --demo
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS expenses (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    spent_on TEXT    NOT NULL,
    category TEXT    NOT NULL,
    amount   REAL    NOT NULL CHECK (amount > 0),
    note     TEXT    NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS budgets (
    category TEXT PRIMARY KEY,
    monthly_limit REAL NOT NULL CHECK (monthly_limit >= 0)
);
CREATE INDEX IF NOT EXISTS idx_expenses_month ON expenses(spent_on);
"""


@contextmanager
def connect(db: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def valid_month(text: str) -> str:
    try:
        date.fromisoformat(f"{text}-01")
    except ValueError as exc:
        raise ValueError(f"invalid month {text!r}; use YYYY-MM") from exc
    return text


def valid_date(text: str) -> str:
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise ValueError(f"invalid date {text!r}; use YYYY-MM-DD") from exc


def add_expense(db: Path, spent_on: str, category: str, amount: float,
                note: str) -> None:
    with connect(db) as conn:
        cur = conn.execute(
            "INSERT INTO expenses (spent_on, category, amount, note) "
            "VALUES (?, ?, ?, ?)",
            (valid_date(spent_on), category.strip().lower(), round(amount, 2), note),
        )
        print(f"recorded expense #{cur.lastrowid}: {amount:.2f} on {category}")


def set_budget(db: Path, category: str, limit: float) -> None:
    with connect(db) as conn:
        conn.execute(
            "INSERT INTO budgets (category, monthly_limit) VALUES (?, ?) "
            "ON CONFLICT(category) DO UPDATE SET monthly_limit = excluded.monthly_limit",
            (category.strip().lower(), limit),
        )
    print(f"budget for {category}: {limit:.2f}/month")


def list_expenses(db: Path, month: str | None, category: str | None) -> None:
    sql = "SELECT id, spent_on, category, amount, note FROM expenses WHERE 1=1"
    params: list[object] = []
    if month:
        sql += " AND substr(spent_on, 1, 7) = ?"
        params.append(month)
    if category:
        sql += " AND category = ?"
        params.append(category.lower())
    sql += " ORDER BY spent_on, id"
    with connect(db) as conn:
        rows = conn.execute(sql, params).fetchall()
    if not rows:
        print("no expenses found")
        return
    print(f"{'id':>4}  {'date':<10}  {'category':<14} {'amount':>9}  note")
    for row in rows:
        print(f"{row['id']:>4}  {row['spent_on']:<10}  {row['category'][:14]:<14} "
              f"{row['amount']:>9.2f}  {row['note']}")
    print(f"total: {sum(r['amount'] for r in rows):.2f}")


def report(db: Path, month: str | None) -> None:
    month = month or date.today().strftime("%Y-%m")
    sql = """
        SELECT e.category,
               COUNT(*)          AS n,
               SUM(e.amount)     AS spent,
               b.monthly_limit   AS budget
        FROM expenses e
        LEFT JOIN budgets b ON b.category = e.category
        WHERE substr(e.spent_on, 1, 7) = ?
        GROUP BY e.category
        ORDER BY spent DESC
    """
    with connect(db) as conn:
        rows = conn.execute(sql, (month,)).fetchall()
    if not rows:
        print(f"no expenses in {month}")
        return
    print(f"Report for {month}")
    print(f"{'category':<16} {'count':>6} {'spent':>10} {'budget':>10} {'left':>10}")
    print("-" * 58)
    total = 0.0
    for row in rows:
        spent = float(row["spent"])
        total += spent
        budget = row["budget"]
        if budget is None:
            budget_text, left_text = "     -", "     -"
        else:
            left = float(budget) - spent
            budget_text = f"{budget:>10.2f}"
            left_text = f"{left:>10.2f}" + ("  OVER" if left < 0 else "")
        print(f"{row['category'][:16]:<16} {row['n']:>6} {spent:>10.2f} "
              f"{budget_text} {left_text}")
    print("-" * 58)
    print(f"{'TOTAL':<16} {'':>6} {total:>10.2f}")


def export_csv(db: Path, dest: Path, month: str | None, force: bool) -> None:
    if dest.exists() and not force:
        raise FileExistsError(f"{dest} exists (use --force)")
    sql = "SELECT spent_on, category, amount, note FROM expenses"
    params: list[object] = []
    if month:
        sql += " WHERE substr(spent_on, 1, 7) = ?"
        params.append(month)
    sql += " ORDER BY spent_on, id"
    with connect(db) as conn:
        rows = conn.execute(sql, params).fetchall()
    with dest.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\r\n")
        writer.writerow(["spent_on", "category", "amount", "note"])
        writer.writerows(tuple(row) for row in rows)
    print(f"exported {len(rows)} rows -> {dest}")


def demo() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "demo.db"
        add_expense(db, "2026-10-01", "food", 12.40, "groceries")
        add_expense(db, "2026-10-03", "transport", 2.75, "bus")
        add_expense(db, "2026-10-07", "food", 31.10, "dinner")
        add_expense(db, "2026-09-28", "books", 18.00, "novel")
        set_budget(db, "food", 50)
        set_budget(db, "transport", 20)
        print()
        list_expenses(db, "2026-10", None)
        print()
        report(db, "2026-10")
        print()
        export_csv(db, Path(tmp) / "out.csv", "2026-10", False)
    return 0


def main(argv: list[str] | None = None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", type=Path, default=argparse.SUPPRESS)

    p = argparse.ArgumentParser(description="SQLite expense tracker.", parents=[common])
    p.add_argument("--demo", action="store_true", help="run an offline demonstration")
    sub = p.add_subparsers(dest="command")

    a = sub.add_parser("add", help="record an expense", parents=[common])
    a.add_argument("date")
    a.add_argument("category")
    a.add_argument("amount", type=float)
    a.add_argument("--note", default="")

    ls = sub.add_parser("list", help="list expenses", parents=[common])
    ls.add_argument("--month")
    ls.add_argument("--category")

    b = sub.add_parser("budget", help="set a monthly budget", parents=[common])
    b.add_argument("category")
    b.add_argument("limit", type=float)

    r = sub.add_parser("report", help="monthly category report", parents=[common])
    r.add_argument("--month")

    e = sub.add_parser("export", help="export to CSV", parents=[common])
    e.add_argument("dest", type=Path)
    e.add_argument("--month")
    e.add_argument("--force", action="store_true")

    args = p.parse_args(argv, argparse.Namespace(db=Path("expenses.db")))
    if args.demo:
        return demo()
    if not args.command:
        p.print_help()
        return 0

    try:
        if args.command == "add":
            if args.amount <= 0:
                print("error: amount must be positive", file=sys.stderr)
                return 2
            add_expense(args.db, args.date, args.category, args.amount, args.note)
        elif args.command == "list":
            month = valid_month(args.month) if args.month else None
            list_expenses(args.db, month, args.category)
        elif args.command == "budget":
            if args.limit < 0:
                print("error: limit must be non-negative", file=sys.stderr)
                return 2
            set_budget(args.db, args.category, args.limit)
        elif args.command == "report":
            month = valid_month(args.month) if args.month else None
            report(args.db, month)
        elif args.command == "export":
            month = valid_month(args.month) if args.month else None
            export_csv(args.db, args.dest, month, args.force)
    except (sqlite3.Error, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
