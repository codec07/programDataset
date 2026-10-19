"""A SQLite-backed contact book with search, tagging and vCard export.

Contacts store name, email, phone, company and a comma-separated tag list.
All writes are parameterised and wrapped in a transaction context manager.

Usage:
    python contact_book.py --db contacts.db add "Ada Lovelace" --email ada@example.com
    python contact_book.py --db contacts.db list --tag friend
    python contact_book.py --db contacts.db search lovelace
    python contact_book.py --db contacts.db edit 1 --phone +44...
    python contact_book.py --db contacts.db delete 1 --dry-run
    python contact_book.py --db contacts.db export contacts.vcf --force
    python contact_book.py --demo
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    email   TEXT NOT NULL DEFAULT '',
    phone   TEXT NOT NULL DEFAULT '',
    company TEXT NOT NULL DEFAULT '',
    tags    TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_contacts_email
    ON contacts(email) WHERE email <> '';
"""

EDITABLE = ("name", "email", "phone", "company", "tags")


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


def normalise_tags(tags: str) -> str:
    cleaned = sorted({t.strip().lower() for t in tags.split(",") if t.strip()})
    return ",".join(cleaned)


def add_contact(db: Path, fields: dict[str, str]) -> int:
    if not fields.get("name", "").strip():
        raise ValueError("name is required")
    values = {key: fields.get(key, "").strip() for key in EDITABLE}
    values["tags"] = normalise_tags(values["tags"])
    with connect(db) as conn:
        cur = conn.execute(
            "INSERT INTO contacts (name, email, phone, company, tags) "
            "VALUES (?, ?, ?, ?, ?)",
            (values["name"], values["email"], values["phone"],
             values["company"], values["tags"]),
        )
        new_id = int(cur.lastrowid or 0)
    print(f"added contact #{new_id}: {values['name']}")
    return new_id


def list_contacts(db: Path, tag: str | None, limit: int) -> None:
    sql = "SELECT id, name, email, phone, company, tags FROM contacts"
    params: list[object] = []
    if tag:
        sql += " WHERE ',' || tags || ',' LIKE ?"
        params.append(f"%,{tag.lower().strip()},%")
    sql += " ORDER BY name COLLATE NOCASE LIMIT ?"
    params.append(limit)
    with connect(db) as conn:
        rows = conn.execute(sql, params).fetchall()
    if not rows:
        print("no contacts found")
        return
    for row in rows:
        detail = "  ".join(part for part in (
            row["email"], row["phone"], row["company"],
            f"[{row['tags']}]" if row["tags"] else "",
        ) if part)
        print(f"{row['id']:>4}  {row['name']:<28} {detail}")


def search(db: Path, term: str) -> None:
    pattern = f"%{term}%"
    sql = ("SELECT id, name, email, phone, company, tags FROM contacts "
           "WHERE name LIKE ? OR email LIKE ? OR phone LIKE ? OR company LIKE ? "
           "OR tags LIKE ? ORDER BY name COLLATE NOCASE")
    with connect(db) as conn:
        rows = conn.execute(sql, (pattern,) * 5).fetchall()
    if not rows:
        print(f"no match for {term!r}")
        return
    for row in rows:
        detail = "  ".join(part for part in (
            f"<{row['email']}>" if row["email"] else "",
            row["phone"], row["company"],
            f"[{row['tags']}]" if row["tags"] else "",
        ) if part)
        print(f"{row['id']:>4}  {row['name']:<24} {detail}")


def edit_contact(db: Path, contact_id: int, updates: dict[str, str],
                 dry_run: bool) -> bool:
    clean = {k: v.strip() for k, v in updates.items() if k in EDITABLE and v is not None}
    if "tags" in clean:
        clean["tags"] = normalise_tags(clean["tags"])
    if not clean:
        print("nothing to update", file=sys.stderr)
        return False
    assignments = ", ".join(f"{col} = ?" for col in clean)
    sql = f"UPDATE contacts SET {assignments} WHERE id = ?"
    params = (*clean.values(), contact_id)
    if dry_run:
        print(f"[dry-run] {sql}\n[dry-run] {params!r}")
        return True
    with connect(db) as conn:
        cur = conn.execute(sql, params)
        changed = cur.rowcount
    print(f"updated {changed} contact(s)")
    return changed > 0


def delete_contact(db: Path, contact_id: int, dry_run: bool) -> bool:
    if dry_run:
        print(f"[dry-run] DELETE FROM contacts WHERE id = ?\n[dry-run] ({contact_id},)")
        return True
    with connect(db) as conn:
        cur = conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        changed = cur.rowcount
    print(f"deleted {changed} contact(s)")
    return changed > 0


def export_vcf(db: Path, dest: Path, force: bool) -> None:
    if dest.exists() and not force:
        raise FileExistsError(f"{dest} exists (use --force)")
    with connect(db) as conn:
        rows = conn.execute("SELECT name, email, phone, company, tags "
                            "FROM contacts ORDER BY name").fetchall()
    lines: list[str] = []
    for row in rows:
        lines.extend([
            "BEGIN:VCARD",
            "VERSION:3.0",
            f"FN:{row['name']}",
            f"N:{row['name']}",
            f"ORG:{row['company']}",
            f"TEL;TYPE=CELL:{row['phone']}",
            f"EMAIL:{row['email']}",
            f"CATEGORIES:{row['tags']}",
            "END:VCARD",
        ])
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"exported {len(rows)} contact(s) -> {dest}")


def demo() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "contacts.db"
        add_contact(db, {"name": "Ada Lovelace", "email": "ada@example.com",
                         "phone": "+44 20 0000 0001", "company": "Analytical",
                         "tags": "friend, math"})
        add_contact(db, {"name": "Grace Hopper", "email": "grace@example.com",
                         "company": "Navy", "tags": "work"})
        add_contact(db, {"name": "Alan Turing", "email": "alan@example.com",
                         "tags": "friend"})
        print()
        list_contacts(db, None, 20)
        print("\ntag=friend")
        list_contacts(db, "friend", 20)
        print("\nsearch=navy")
        search(db, "navy")
        print()
        edit_contact(db, 3, {"company": "Bletchley Park"}, False)
        delete_contact(db, 2, False)
        print()
        export_vcf(db, Path(tmp) / "contacts.vcf", False)
    return 0


def main(argv: list[str] | None = None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", type=Path, default=argparse.SUPPRESS)
    common.add_argument("--dry-run", action="store_true", default=argparse.SUPPRESS)

    p = argparse.ArgumentParser(description="SQLite contact book.", parents=[common])
    p.add_argument("--demo", action="store_true")
    sub = p.add_subparsers(dest="command")

    a = sub.add_parser("add", help="add a contact", parents=[common])
    a.add_argument("name")
    a.add_argument("--email", default="")
    a.add_argument("--phone", default="")
    a.add_argument("--company", default="")
    a.add_argument("--tags", default="")

    ls = sub.add_parser("list", help="list contacts", parents=[common])
    ls.add_argument("--tag")
    ls.add_argument("--limit", type=int, default=50)

    s = sub.add_parser("search", help="search all fields", parents=[common])
    s.add_argument("term")

    e = sub.add_parser("edit", help="edit a contact", parents=[common])
    e.add_argument("id", type=int)
    e.add_argument("--name")
    e.add_argument("--email")
    e.add_argument("--phone")
    e.add_argument("--company")
    e.add_argument("--tags")

    d = sub.add_parser("delete", help="delete a contact", parents=[common])
    d.add_argument("id", type=int)

    x = sub.add_parser("export", help="export vCard 3.0", parents=[common])
    x.add_argument("dest", type=Path)
    x.add_argument("--force", action="store_true")

    args = p.parse_args(argv, argparse.Namespace(db=Path("contacts.db"),
                                                 dry_run=False))
    if args.demo:
        return demo()
    if not args.command:
        p.print_help()
        return 0

    try:
        if args.command == "add":
            add_contact(args.db, {"name": args.name, "email": args.email,
                                  "phone": args.phone, "company": args.company,
                                  "tags": args.tags})
        elif args.command == "list":
            list_contacts(args.db, args.tag, max(1, args.limit))
        elif args.command == "search":
            search(args.db, args.term)
        elif args.command == "edit":
            updates = {k: getattr(args, k) for k in EDITABLE
                       if getattr(args, k) is not None}
            if not edit_contact(args.db, args.id, updates, args.dry_run):
                return 1
        elif args.command == "delete":
            if not delete_contact(args.db, args.id, args.dry_run):
                return 1
        elif args.command == "export":
            export_vcf(args.db, args.dest, args.force)
    except (sqlite3.Error, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
