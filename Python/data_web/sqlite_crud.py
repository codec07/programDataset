"""Command-line CRUD inventory backed by SQLite with safe, parameterised SQL.

Schema:
    items(id INTEGER PK, name TEXT UNIQUE, category TEXT, quantity INTEGER,
          price REAL, notes TEXT, created_at TEXT)

Every statement uses ``?`` placeholders and a transaction context manager.
Write commands support ``--dry-run`` to show the SQL and parameters without
committing.

Usage:
    python sqlite_crud.py --db stock.db init
    python sqlite_crud.py --db stock.db add Widget tools 12 4.50 --notes "bin A"
    python sqlite_crud.py --db stock.db list --category tools
    python sqlite_crud.py --db stock.db update 1 --quantity 20
    python sqlite_crud.py --db stock.db delete 1 --dry-run
    python sqlite_crud.py --demo
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    category   TEXT    NOT NULL DEFAULT 'general',
    quantity   INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    price      REAL    NOT NULL DEFAULT 0.0 CHECK (price >= 0),
    notes      TEXT    NOT NULL DEFAULT '',
    created_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);
"""


@contextmanager
def connect(db: Path) -> Iterator[sqlite3.Connection]:
    """Open a connection, commit on success, roll back on error, always close."""
    conn = sqlite3.connect(db, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db: Path) -> None:
    with connect(db) as conn:
        conn.executescript(SCHEMA)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def add_item(db: Path, name: str, category: str, quantity: int, price: float,
             notes: str, dry_run: bool) -> int:
    sql = ("INSERT INTO items (name, category, quantity, price, notes, created_at) "
           "VALUES (?, ?, ?, ?, ?, ?)")
    params = (name, category, quantity, price, notes, now_iso())
    if dry_run:
        print(f"[dry-run] {sql}\n[dry-run] params={params!r}")
        return 0
    with connect(db) as conn:
        cur = conn.execute(sql, params)
        new_id = int(cur.lastrowid or 0)
    print(f"added item id={new_id} name={name!r}")
    return new_id


def list_items(db: Path, category: str | None, limit: int) -> None:
    sql = "SELECT id, name, category, quantity, price, notes FROM items"
    params: list[Any] = []
    if category:
        sql += " WHERE category = ?"
        params.append(category)
    sql += " ORDER BY id LIMIT ?"
    params.append(limit)
    with connect(db) as conn:
        rows = conn.execute(sql, params).fetchall()
    if not rows:
        print("no items found")
        return
    print(f"{'id':>4}  {'name':<20} {'category':<12} {'qty':>5} {'price':>9}")
    print("-" * 56)
    for row in rows:
        print(f"{row['id']:>4}  {row['name'][:20]:<20} {row['category'][:12]:<12} "
              f"{row['quantity']:>5} {row['price']:>9.2f}")
        if row["notes"]:
            print(f"      note: {row['notes']}")


def update_item(db: Path, item_id: int, fields: dict[str, Any], dry_run: bool) -> bool:
    if not fields:
        print("nothing to update", file=sys.stderr)
        return False
    # Column names come from a fixed allow-list, never from raw user input.
    allowed = {"name", "category", "quantity", "price", "notes", "created_at"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"unknown columns: {', '.join(sorted(unknown))}")
    assignments = ", ".join(f"{col} = ?" for col in fields)
    sql = f"UPDATE items SET {assignments} WHERE id = ?"
    params = (*fields.values(), item_id)
    if dry_run:
        print(f"[dry-run] {sql}\n[dry-run] params={params!r}")
        return True
    with connect(db) as conn:
        cur = conn.execute(sql, params)
        changed = cur.rowcount
    print(f"updated {changed} row(s)")
    return changed > 0


def delete_item(db: Path, item_id: int, dry_run: bool) -> bool:
    sql = "DELETE FROM items WHERE id = ?"
    if dry_run:
        print(f"[dry-run] {sql}\n[dry-run] params=({item_id},)")
        return True
    with connect(db) as conn:
        cur = conn.execute(sql, (item_id,))
        changed = cur.rowcount
    print(f"deleted {changed} row(s)")
    return changed > 0


def show_stats(db: Path) -> None:
    sql = ("SELECT category, COUNT(*) AS n, SUM(quantity) AS units, "
           "SUM(quantity * price) AS value FROM items GROUP BY category "
           "ORDER BY value DESC")
    with connect(db) as conn:
        rows = conn.execute(sql).fetchall()
    if not rows:
        print("inventory is empty")
        return
    print(f"{'category':<16} {'items':>6} {'units':>7} {'value':>12}")
    for r in rows:
        print(f"{r['category']:<16} {r['n']:>6} {r['units'] or 0:>7} "
              f"{r['value'] or 0:>12.2f}")


def demo() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "demo.db"
        init_db(db)
        add_item(db, "Cable", "tools", 5, 3.25, "USB-C", False)
        add_item(db, "Widget", "tools", 12, 4.50, "bin A", False)
        add_item(db, "Manual", "docs", 2, 0.0, "", False)
        try:
            add_item(db, "Widget", "tools", 1, 4.50, "duplicate", False)
        except sqlite3.IntegrityError as exc:
            print(f"expected constraint error: {exc}")
        list_items(db, None, 50)
        print()
        update_item(db, 1, {"quantity": 9}, False)
        delete_item(db, 3, False)
        print()
        show_stats(db)
    return 0


def main(argv: list[str] | None = None) -> int:
    # SUPPRESS defaults keep a subparser from resetting options given earlier.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", type=Path, default=argparse.SUPPRESS,
                        help="database file")
    common.add_argument("--dry-run", action="store_true", default=argparse.SUPPRESS,
                        help="print SQL without executing")

    p = argparse.ArgumentParser(description="SQLite inventory CRUD.", parents=[common])
    p.add_argument("--demo", action="store_true", help="run an offline demonstration")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("init", help="create tables", parents=[common])
    a = sub.add_parser("add", help="insert an item", parents=[common])
    a.add_argument("name")
    a.add_argument("category", nargs="?", default="general")
    a.add_argument("quantity", nargs="?", type=int, default=0)
    a.add_argument("price", nargs="?", type=float, default=0.0)
    a.add_argument("--notes", default="")

    ls = sub.add_parser("list", help="list items", parents=[common])
    ls.add_argument("--category")
    ls.add_argument("--limit", type=int, default=50)

    u = sub.add_parser("update", help="update an item", parents=[common])
    u.add_argument("id", type=int)
    u.add_argument("--name")
    u.add_argument("--category")
    u.add_argument("--quantity", type=int)
    u.add_argument("--price", type=float)
    u.add_argument("--notes")

    d = sub.add_parser("delete", help="delete an item", parents=[common])
    d.add_argument("id", type=int)

    sub.add_parser("stats", help="aggregate inventory value", parents=[common])

    args = p.parse_args(argv, argparse.Namespace(db=Path("inventory.db"),
                                                 dry_run=False))
    if args.demo:
        return demo()
    if not args.command:
        p.print_help()
        return 0

    try:
        if args.command != "init" and not args.db.exists():
            print(f"error: database not found: {args.db} (run init first)",
                  file=sys.stderr)
            return 2
        if args.command == "init":
            init_db(args.db)
            print(f"initialised {args.db}")
        elif args.command == "add":
            if args.quantity < 0 or args.price < 0:
                print("error: quantity and price must be non-negative", file=sys.stderr)
                return 2
            add_item(args.db, args.name, args.category, args.quantity, args.price,
                     args.notes, args.dry_run)
        elif args.command == "list":
            list_items(args.db, args.category, max(1, args.limit))
        elif args.command == "update":
            fields = {k: v for k, v in {
                "name": args.name, "category": args.category,
                "quantity": args.quantity, "price": args.price,
                "notes": args.notes,
            }.items() if v is not None}
            if not update_item(args.db, args.id, fields, args.dry_run):
                return 1
        elif args.command == "delete":
            if not delete_item(args.db, args.id, args.dry_run):
                return 1
        elif args.command == "stats":
            show_stats(args.db)
    except (sqlite3.Error, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
